function formatCurrency(value) {
    return `Rs ${new Intl.NumberFormat("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(value)}`;
}

function calculateLoanBreakdown(principal, annualRate, months) {
    const monthlyRate = annualRate / 12 / 100;
    let emi = 0;

    if (monthlyRate === 0) {
        emi = principal / months;
    } else {
        const pow = Math.pow(1 + monthlyRate, months);
        emi = (principal * monthlyRate * pow) / (pow - 1);
    }

    const totalPayment = emi * months;
    const totalInterest = totalPayment - principal;

    return {
        emi,
        totalPayment,
        totalInterest,
        installments: months,
    };
}

function renderApplyEligibility() {
    const incomeInput = document.getElementById("apply-income");
    const loanInput = document.getElementById("apply-loan-amount");
    const output = document.getElementById("apply-eligibility-result");

    if (!incomeInput || !loanInput || !output) {
        return;
    }

    const income = Number(incomeInput.value || 0);
    const loan = Number(loanInput.value || 0);

    if (!income || !loan) {
        output.innerHTML = "Eligibility preview: enter income and loan amount.";
        return;
    }

    const maxEligible = income * 20;
    if (income >= 15000 && loan <= maxEligible) {
        output.innerHTML = `<span class="text-success">Likely eligible. Maximum estimate: <strong>${formatCurrency(maxEligible)}</strong></span>`;
    } else {
        output.innerHTML = `<span class="text-danger">Not eligible based on current values. Maximum estimate: <strong>${formatCurrency(maxEligible)}</strong></span>`;
    }
}

function renderApplyLoanBreakdown() {
    const amountInput = document.getElementById("apply-loan-amount");
    const rateInput = document.getElementById("apply-interest-rate");
    const tenureInput = document.getElementById("apply-tenure-months");
    const output = document.getElementById("apply-loan-breakdown");

    if (!amountInput || !rateInput || !tenureInput || !output) {
        return;
    }

    const principal = Number(amountInput.value || 0);
    const rate = Number(rateInput.value || 0);
    const months = Number(tenureInput.value || 0);

    if (principal <= 0 || months <= 0 || rate < 0) {
        output.innerHTML = "EMI preview: enter amount, interest rate, and installments.";
        return;
    }

    const breakdown = calculateLoanBreakdown(principal, rate, months);
    output.innerHTML = `
        <div><strong>EMI / Month:</strong> ${formatCurrency(breakdown.emi)}</div>
        <div><strong>Installments:</strong> ${breakdown.installments}</div>
        <div><strong>Total Interest:</strong> ${formatCurrency(breakdown.totalInterest)}</div>
        <div><strong>Total Payable:</strong> ${formatCurrency(breakdown.totalPayment)}</div>
    `;
}

let otpAbortController = null;

function startOtpAutoRead(otpInput, statusEl, verifyCallback) {
    const webOtpSupported = "OTPCredential" in window;
    const secureForWebOtp =
        window.location.protocol === "https:" ||
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";

    if (!webOtpSupported || !secureForWebOtp || !otpInput) {
        return;
    }

    if (otpAbortController) {
        otpAbortController.abort();
    }

    otpAbortController = new AbortController();

    navigator.credentials
        .get({ otp: { transport: ["sms"] }, signal: otpAbortController.signal })
        .then((otpCredential) => {
            if (!otpCredential || !otpCredential.code) {
                return;
            }
            otpInput.value = otpCredential.code;
            if (statusEl) {
                statusEl.innerHTML = "<span class='text-info'>OTP auto-captured from SMS. Verifying...</span>";
            }
            if (verifyCallback) {
                verifyCallback();
            }
        })
        .catch(() => {
            // Ignore WebOTP failures. Manual entry is fallback.
        });
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    return { ok: response.ok, data };
}

document.addEventListener("DOMContentLoaded", () => {
    const yearEl = document.getElementById("footer-year");
    if (yearEl) {
        yearEl.textContent = new Date().getFullYear();
    }

    const emiForm = document.getElementById("emi-form");
    if (emiForm) {
        emiForm.addEventListener("submit", (event) => {
            event.preventDefault();
            const principal = Number(document.getElementById("emi-amount").value || 0);
            const rate = Number(document.getElementById("emi-rate").value || 0);
            const months = Number(document.getElementById("emi-tenure").value || 0);
            const result = document.getElementById("emi-result");

            if (principal <= 0 || months <= 0 || rate < 0) {
                result.innerHTML = '<span class="text-danger">Please enter valid EMI values.</span>';
                return;
            }

            const breakdown = calculateLoanBreakdown(principal, rate, months);
            result.innerHTML = `
                <div><strong>Monthly EMI:</strong> ${formatCurrency(breakdown.emi)}</div>
                <div><strong>Installments:</strong> ${breakdown.installments}</div>
                <div><strong>Total Interest:</strong> ${formatCurrency(breakdown.totalInterest)}</div>
                <div><strong>Total Payment:</strong> ${formatCurrency(breakdown.totalPayment)}</div>
            `;
        });
    }

    const eligibilityForm = document.getElementById("eligibility-form");
    if (eligibilityForm) {
        eligibilityForm.addEventListener("submit", (event) => {
            event.preventDefault();
            const income = Number(document.getElementById("elig-income").value || 0);
            const existingEmi = Number(document.getElementById("elig-existing-emi").value || 0);
            const requestedLoan = Number(document.getElementById("elig-loan").value || 0);
            const result = document.getElementById("eligibility-result");

            if (income <= 0 || requestedLoan <= 0 || existingEmi < 0) {
                result.innerHTML = '<span class="text-danger">Please enter valid eligibility values.</span>';
                return;
            }

            const maxByIncome = income * 20;
            const adjustedMax = Math.max(0, maxByIncome - existingEmi * 50);
            const eligible = income >= 15000 && requestedLoan <= adjustedMax;

            if (eligible) {
                result.innerHTML = `<span class="text-success">Eligible. Estimated maximum: <strong>${formatCurrency(adjustedMax)}</strong></span>`;
            } else {
                result.innerHTML = `<span class="text-danger">Not eligible now. Estimated maximum: <strong>${formatCurrency(adjustedMax)}</strong></span>`;
            }
        });
    }

    const applyIncome = document.getElementById("apply-income");
    const applyLoan = document.getElementById("apply-loan-amount");
    const applyRate = document.getElementById("apply-interest-rate");
    const applyTenure = document.getElementById("apply-tenure-months");
    if (applyIncome && applyLoan) {
        applyIncome.addEventListener("input", renderApplyEligibility);
        applyLoan.addEventListener("input", renderApplyEligibility);
        renderApplyEligibility();
    }
    if (applyLoan && applyRate && applyTenure) {
        applyLoan.addEventListener("input", renderApplyLoanBreakdown);
        applyRate.addEventListener("input", renderApplyLoanBreakdown);
        applyTenure.addEventListener("input", renderApplyLoanBreakdown);
        renderApplyLoanBreakdown();
    }

    const sendOtpBtn = document.getElementById("send-otp-btn");
    const verifyOtpBtn = document.getElementById("verify-otp-btn");
    const otpStatus = document.getElementById("otp-status");
    const phoneInput = document.getElementById("register-phone");
    const otpInput = document.getElementById("register-otp");

    async function verifyOtpFlow() {
        if (!phoneInput || !otpInput || !otpStatus) {
            return;
        }

        const phone = phoneInput.value.trim();
        const otp = otpInput.value.trim();

        if (!phone || !otp) {
            otpStatus.innerHTML = "<span class='text-danger'>Enter phone and OTP first.</span>";
            return;
        }

        otpStatus.innerHTML = "<span class='text-info'>Verifying OTP...</span>";
        const { ok, data } = await postJson("/api/auth/verify-otp", {
            phone,
            otp,
            purpose: "register",
        });

        if (ok && data.success) {
            otpStatus.innerHTML = "<span class='text-success'>Phone verified successfully. You can now register.</span>";
            return;
        }

        otpStatus.innerHTML = `<span class='text-danger'>${data.message || "OTP verification failed."}</span>`;
    }

    if (sendOtpBtn) {
        sendOtpBtn.addEventListener("click", async () => {
            if (!phoneInput || !otpStatus || !otpInput) {
                return;
            }

            const phone = phoneInput.value.trim();
            if (!phone) {
                otpStatus.innerHTML = "<span class='text-danger'>Enter phone number before requesting OTP.</span>";
                return;
            }

            otpStatus.innerHTML = "<span class='text-info'>Sending OTP...</span>";
            const { ok, data } = await postJson("/api/auth/send-otp", {
                phone,
                purpose: "register",
            });

            if (ok && data.success) {
                const demo = data.demo_otp
                    ? ` Demo OTP (dev mode): <strong>${data.demo_otp}</strong>`
                    : "";
                otpStatus.innerHTML = `<span class='text-success'>${data.message}</span>${demo}`;
                startOtpAutoRead(otpInput, otpStatus, verifyOtpFlow);
                return;
            }

            otpStatus.innerHTML = `<span class='text-danger'>${data.message || "Failed to send OTP."}</span>`;
        });
    }

    if (verifyOtpBtn) {
        verifyOtpBtn.addEventListener("click", verifyOtpFlow);
    }
});
