/**
 * Validates a credit card number using the Luhn algorithm.
 * @param cardNumber The card number string (can contain spaces or dashes)
 * @returns boolean true if valid, false otherwise
 */
export const validateLuhn = (cardNumber: string): boolean => {
    // Remove all non-digit characters
    const sanitized = cardNumber.replace(/\D/g, '');

    // Check if empty or too short
    if (!sanitized || sanitized.length < 13 || sanitized.length > 19) {
        return false;
    }

    let sum = 0;
    let shouldDouble = false;

    // Loop through values from right to left
    for (let i = sanitized.length - 1; i >= 0; i--) {
        let digit = parseInt(sanitized.charAt(i), 10);

        if (shouldDouble) {
            digit *= 2;
            if (digit > 9) {
                digit -= 9;
            }
        }

        sum += digit;
        shouldDouble = !shouldDouble;
    }

    return (sum % 10) === 0;
};

/**
 * Validates card expiry date (MM/YY)
 */
export const validateExpiry = (expiry: string): boolean => {
    if (!/^\d{2}\/\d{2}$/.test(expiry)) return false;

    const [month, year] = expiry.split('/').map(n => parseInt(n, 10));
    if (month < 1 || month > 12) return false;

    const now = new Date();
    const currentYear = now.getFullYear() % 100;
    const currentMonth = now.getMonth() + 1;

    if (year < currentYear) return false;
    if (year === currentYear && month < currentMonth) return false;

    return true;
};

/**
 * Validates CVC
 */
export const validateCVC = (cvc: string): boolean => {
    return /^\d{3,4}$/.test(cvc);
};
