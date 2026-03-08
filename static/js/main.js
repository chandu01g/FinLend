function formatCurrency(value) {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
    }).format(value);
}

function calculateEMI(principal, annualRate, months) {
    const monthlyRate = annualRate / 12 / 100;

    if (monthlyRate === 0) {
        return principal / months;
    }

    const pow = Math.pow(1 + monthlyRate, months);
    return (principal * monthlyRate * pow) / (pow - 1);
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

            const emi = calculateEMI(principal, rate, months);
            const totalPayment = emi * months;
            const totalInterest = totalPayment - principal;

            result.innerHTML = `
                <div><strong>Monthly EMI:</strong> ${formatCurrency(emi)}</div>
                <div><strong>Total Interest:</strong> ${formatCurrency(totalInterest)}</div>
                <div><strong>Total Payment:</strong> ${formatCurrency(totalPayment)}</div>
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
    if (applyIncome && applyLoan) {
        applyIncome.addEventListener("input", renderApplyEligibility);
        applyLoan.addEventListener("input", renderApplyEligibility);
        renderApplyEligibility();
    }
});
