//! Modular constraint filtering for the Kangaroo ECDLP solver
//!
//! When the private key k is known to satisfy k ≡ R (mod M), the search space
//! can be reduced by a factor of M. Instead of searching for k directly,
//! we search for j such that k = R + M*j, transforming:
//!   - Base point: G → H = M*G
//!   - Public key: P → Q = P - R*G
//!   - Range: 2^range_bits → 2^range_bits / M
//!
//! Supports M and R up to 256 bits (full secp256k1 scalar range).

use anyhow::{anyhow, Result};
use k256::elliptic_curve::ops::{MulByGenerator, Reduce};
use k256::U256 as K256U256;
use k256::{ProjectivePoint, Scalar};

/// Parse a hex string into a 256-bit big-endian byte array.
/// Supports values up to 2^256 - 1 (full secp256k1 scalar range).
fn parse_u256_hex(hex: &str) -> Result<[u8; 32]> {
    let clean = hex.trim_start_matches("0x");
    if clean.is_empty() {
        return Ok([0u8; 32]);
    }
    if clean.len() > 64 {
        return Err(anyhow!(
            "Value too large for U256: {} hex chars (max 64)",
            clean.len()
        ));
    }
    let padded = format!("{:0>64}", clean);
    let bytes = hex::decode(&padded).map_err(|e| anyhow!("Invalid hex: {e}"))?;
    let mut result = [0u8; 32];
    result.copy_from_slice(&bytes);
    Ok(result)
}

/// Compare two big-endian 256-bit byte arrays: returns true if a >= b.
fn u256_be_gte(a: &[u8; 32], b: &[u8; 32]) -> bool {
    for i in 0..32 {
        if a[i] > b[i] {
            return true;
        }
        if a[i] < b[i] {
            return false;
        }
    }
    true // equal
}

/// Check if a 256-bit big-endian value is zero.
fn u256_be_is_zero(v: &[u8; 32]) -> bool {
    v.iter().all(|&b| b == 0)
}

/// Compute floor(log2(v)) for a big-endian 256-bit value. Returns 0 for zero.
fn u256_be_log2_floor(v: &[u8; 32]) -> u32 {
    for i in 0..32 {
        if v[i] != 0 {
            let byte_log = 7 - (v[i].leading_zeros() as u32);
            return (31 - i as u32) * 8 + byte_log;
        }
    }
    0
}

/// Subtract b from a in big-endian 256-bit, returning result as LE bytes.
/// Assumes a >= b. If a < b, returns zero.
fn u256_be_sub_to_le(a: &[u8; 32], b: &[u8; 32]) -> [u8; 32] {
    let mut result_be = [0u8; 32];
    let mut borrow: i16 = 0;
    for i in (0..32).rev() {
        let diff = a[i] as i16 - b[i] as i16 - borrow;
        if diff < 0 {
            result_be[i] = (diff + 256) as u8;
            borrow = 1;
        } else {
            result_be[i] = diff as u8;
            borrow = 0;
        }
    }
    if borrow != 0 {
        return [0u8; 32];
    }
    // Convert BE result to LE
    let mut result_le = [0u8; 32];
    for i in 0..32 {
        result_le[i] = result_be[31 - i];
    }
    result_le
}

/// Divide a 256-bit LE number by a 256-bit BE divisor.
/// Returns (quotient_le, remainder_le). Uses bit-by-bit long division.
fn div_u256_le_by_u256_be(dividend_le: &[u8; 32], divisor_be: &[u8; 32]) -> ([u8; 32], [u8; 32]) {
    // Convert divisor to LE for easier arithmetic
    let mut divisor_le = [0u8; 32];
    for i in 0..32 {
        divisor_le[i] = divisor_be[31 - i];
    }

    // Check if divisor is zero
    if divisor_le.iter().all(|&b| b == 0) {
        return ([0u8; 32], [0u8; 32]);
    }

    // Bit-by-bit long division
    let mut quotient = [0u8; 32];
    let mut remainder = [0u8; 32];

    for bit_pos in (0..256).rev() {
        let byte_idx = bit_pos / 8;
        let bit_idx = bit_pos % 8;
        let dividend_bit = (dividend_le[byte_idx] >> bit_idx) & 1;

        // Shift remainder left by 1 and add next bit of dividend
        let mut carry = dividend_bit;
        for i in 0..32 {
            let new_carry = (remainder[i] >> 7) & 1;
            remainder[i] = (remainder[i] << 1) | carry;
            carry = new_carry;
        }

        // Compare remainder >= divisor
        let mut rem_ge_div = true;
        for i in (0..32).rev() {
            if remainder[i] > divisor_le[i] {
                rem_ge_div = true;
                break;
            }
            if remainder[i] < divisor_le[i] {
                rem_ge_div = false;
                break;
            }
        }

        if rem_ge_div {
            // Subtract divisor from remainder
            let mut borrow: i16 = 0;
            for i in 0..32 {
                let diff = remainder[i] as i16 - divisor_le[i] as i16 - borrow;
                if diff < 0 {
                    remainder[i] = (diff + 256) as u8;
                    borrow = 1;
                } else {
                    remainder[i] = diff as u8;
                    borrow = 0;
                }
            }
            // Set quotient bit
            quotient[byte_idx] |= 1 << bit_idx;
        }
    }

    (quotient, remainder)
}

/// Add 1 to a 256-bit LE number.
fn add_one_u256_le(le_bytes: &[u8; 32]) -> [u8; 32] {
    let mut result = *le_bytes;
    for chunk in 0..4 {
        let offset = chunk * 8;
        let limb = u64::from_le_bytes(result[offset..offset + 8].try_into().unwrap());
        let (sum, overflow) = limb.overflowing_add(1);
        result[offset..offset + 8].copy_from_slice(&sum.to_le_bytes());
        if !overflow {
            break;
        }
    }
    result
}

/// Modular constraint parameters for transformed ECDLP search.
///
/// If k ≡ R (mod M), substitute k = R + M*j and solve j*H = Q
/// where H = M*G and Q = P - R*G.
pub struct ModConstraint {
    /// H = M * G — the new base point
    pub base_point: ProjectivePoint,
    /// Q = P - R * G — the transformed public key
    pub transformed_pubkey: ProjectivePoint,
    /// Starting index j = ceil((start - R) / M) as LE bytes
    pub j_start: [u8; 32],
    /// Bits needed for reduced range: ~range_bits - log2(M)
    pub effective_range_bits: u32,
    /// M as Scalar
    pub mod_step: Scalar,
    /// R as Scalar (0 ≤ R < M)
    pub mod_start: Scalar,
}

impl ModConstraint {
    /// Create a new modular constraint.
    ///
    /// # Arguments
    /// - `mod_step_hex`: M as hex string (e.g. "7" for M=7). Must be ≥ 1.
    /// - `mod_start_hex`: R as hex string (e.g. "0" for R=0). Must be 0 ≤ R < M.
    /// - `pubkey`: original public key P
    /// - `start`: search range start as LE bytes [u8; 32]
    /// - `range_bits`: original range bits
    ///
    /// # Returns
    /// - `Ok(None)` if M=1 and R=0 (no constraint, caller uses default path)
    /// - `Ok(Some(constraint))` if M > 1
    /// - `Err(...)` if M=0, R >= M, or hex parse fails
    pub fn new(
        mod_step_hex: &str,
        mod_start_hex: &str,
        pubkey: &ProjectivePoint,
        start: &[u8; 32],
        range_bits: u32,
    ) -> Result<Option<Self>> {
        // Parse M and R as full 256-bit big-endian values
        let m_be = parse_u256_hex(mod_step_hex)?;
        let r_be = parse_u256_hex(mod_start_hex)?;

        // Validate M >= 1
        if u256_be_is_zero(&m_be) {
            return Err(anyhow!("mod_step M must be >= 1, got 0"));
        }

        // Validate R < M
        if u256_be_gte(&r_be, &m_be) {
            return Err(anyhow!("mod_start R must be < M"));
        }

        // M=1, R=0 → identity constraint, no transformation needed
        let r_is_zero = u256_be_is_zero(&r_be);
        if u256_be_is_zero(&m_be) == false && m_be[31] == 1 && m_be[..31].iter().all(|&b| b == 0) && r_is_zero {
            return Ok(None);
        }

        // Convert to Scalar for curve operations
        let mod_step = <Scalar as Reduce<K256U256>>::reduce(K256U256::from_be_slice(&m_be));
        let mod_start = <Scalar as Reduce<K256U256>>::reduce(K256U256::from_be_slice(&r_be));

        // H = M * G
        let base_point = ProjectivePoint::mul_by_generator(&mod_step);

        // Q = P - R * G
        let transformed_pubkey = if r_is_zero {
            *pubkey
        } else {
            let r_g = ProjectivePoint::mul_by_generator(&mod_start);
            *pubkey - r_g
        };

        // j_start = ceil((start - R) / M) using full 256-bit arithmetic
        // start is LE [u8; 32], M and R are BE [u8; 32]
        // Convert start from LE to BE for subtraction
        let mut start_be = [0u8; 32];
        for i in 0..32 {
            start_be[i] = start[31 - i];
        }

        let diff_le = u256_be_sub_to_le(&start_be, &r_be);
        // diff_le is already in LE format, which is what div_u256_le_by_u256_be expects

        let (quotient_le, remainder_le) = div_u256_le_by_u256_be(&diff_le, &m_be);

        // ceil: if remainder > 0, add 1
        let remainder_is_zero = remainder_le.iter().all(|&b| b == 0);
        let j_start = if !remainder_is_zero {
            add_one_u256_le(&quotient_le)
        } else {
            quotient_le
        };

        // effective_range_bits = range_bits - floor(log2(M)), minimum 1
        let log2_m = u256_be_log2_floor(&m_be);
        let effective_range_bits = range_bits.saturating_sub(log2_m).max(1);

        Ok(Some(Self {
            base_point,
            transformed_pubkey,
            j_start,
            effective_range_bits,
            mod_step,
            mod_start,
        }))
    }
}