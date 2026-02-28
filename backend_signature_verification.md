# Oasis Backend: MetaMask Signature Verification (Node.js)

This document provides the Node.js code snippet for verifying MetaMask signatures on the backend. This is a crucial security step to ensure that requests to protected API endpoints are genuinely from the owner of a specific wallet address.

---

## 1. Core Concept: Sign & Verify

The flow is as follows:

1.  **Frontend**: The user wants to perform a protected action (e.g., access a private dashboard). The frontend asks MetaMask to sign a specific, structured message using the user's private key. This signature does **not** create a blockchain transaction and costs no gas.
2.  **Frontend to Backend**: The frontend sends the original message, the user's wallet address, and the generated signature to your backend API.
3.  **Backend**: The backend receives this data and uses cryptographic functions to verify that the signature could **only** have been created by the private key corresponding to the provided wallet address signing the **exact** same message.

This proves ownership of the wallet without requiring the user to send a transaction or expose their private key.

---

## 2. Backend Implementation (Node.js + Express + Ethers)

This example uses the popular `ethers` library for its robust and easy-to-use cryptographic utilities.

### Prerequisites

Install the necessary packages:

```bash
# Using pnpm (recommended)
pnpm install express ethers

# Or using npm
npm install express ethers
```

### Code: `server.js`

```javascript
const express = require('express');
const { verifyMessage } = require('ethers');

const app = express();
app.use(express.json()); // Middleware to parse JSON bodies

// A simple in-memory store for nonces to prevent replay attacks
const nonces = {};

/**
 * @route   GET /api/auth/nonce/:address
 * @desc    Get a unique, single-use message for a user to sign
 * @access  Public
 */
app.get('/api/auth/nonce/:address', (req, res) => {
    const address = req.params.address.toLowerCase();
    const nonce = `oasis-auth-${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;
    nonces[address] = nonce; // Store the nonce for this address

    console.log(`[AUTH] Issued nonce for ${address}: ${nonce}`);
    res.json({ nonce });
});

/**
 * @route   POST /api/auth/verify
 * @desc    Verify a signed message and grant access (e.g., issue a JWT)
 * @access  Public
 */
app.post('/api/auth/verify', (req, res) => {
    const { address, signature } = req.body;
    const lowerAddr = address.toLowerCase();

    // 1. Get the nonce we issued for this address
    const originalMessage = nonces[lowerAddr];
    if (!originalMessage) {
        console.warn(`[AUTH-FAIL] No nonce found for address: ${lowerAddr}`);
        return res.status(400).json({ error: 'Authentication failed. Please request a new message to sign.' });
    }

    try {
        // 2. Cryptographically verify the signature
        const recoveredAddress = verifyMessage(originalMessage, signature);

        // 3. Check if the recovered address matches the provided address
        if (recoveredAddress.toLowerCase() === lowerAddr) {
            console.log(`[AUTH-SUCCESS] Signature verified for ${lowerAddr}`);

            // 4. IMPORTANT: Invalidate the nonce after use to prevent replay attacks
            delete nonces[lowerAddr];

            // 5. SUCCESS: At this point, you know the user owns the address.
            // You can now issue a session token, JWT, or grant access.
            res.json({
                success: true,
                message: 'Wallet ownership verified.',
                // Example: issue a JWT for session management
                // token: generateJwtForUser(lowerAddr)
            });

        } else {
            console.warn(`[AUTH-FAIL] Signature mismatch. Expected ${lowerAddr}, got ${recoveredAddress}`);
            res.status(401).json({ error: 'Signature verification failed. Wallet ownership could not be proven.' });
        }
    } catch (error) {
        console.error('[AUTH-ERROR] Error during verification:', error);
        res.status(500).json({ error: 'An error occurred during signature verification.' });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Oasis Auth Server running on port ${PORT}`));

```

---

## 3. Frontend Integration

On the frontend, you would first fetch the nonce, then ask MetaMask to sign it.

```javascript
// Assume 'wallet.address' is available after connecting MetaMask

async function loginWithWallet() {
    if (!wallet.address) {
        console.error('Wallet not connected.');
        return;
    }

    try {
        // 1. Fetch the unique message (nonce) to sign from the backend
        const nonceRes = await fetch(`/api/auth/nonce/${wallet.address}`);
        const { nonce } = await nonceRes.json();

        if (!nonce) {
            throw new Error('Could not retrieve nonce from server.');
        }

        // 2. Ask MetaMask to sign the message
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [nonce, wallet.address],
        });

        // 3. Send the address, and signature to the backend for verification
        const verifyRes = await fetch('/api/auth/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address: wallet.address, signature }),
        });

        const verifyData = await verifyRes.json();

        if (verifyRes.ok && verifyData.success) {
            console.log('Backend verification successful!', verifyData);
            // You are now authenticated. Save the JWT, redirect, etc.
            // localStorage.setItem('authToken', verifyData.token);
        } else {
            throw new Error(verifyData.error || 'Verification failed.');
        }

    } catch (error) {
        console.error('Authentication error:', error);
        // Handle errors (e.g., user rejected signature)
    }
}
```

This setup provides a secure, gas-less way to authenticate users and protect your backend resources, ensuring that only the true owner of a wallet can access their associated data.
