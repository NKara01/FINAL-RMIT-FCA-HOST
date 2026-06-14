const stripe = Stripe(window.STRIPE_PUBLIC_KEY);

let elements = null;

const detailsForm = document.getElementById("details-form");
const continueButton = document.getElementById("continue-button");
const payButton = document.getElementById("pay-button");
const paymentMessage = document.getElementById("payment-message");
const paymentElementWrapper = document.getElementById("payment-element-wrapper");
const paymentCardLocked = document.getElementById("payment-card-locked");
const addressInput = document.getElementById("address");

const paymentAppearance = {
    theme: "stripe",
    variables: {
        colorPrimary: "#0e7a4f",
        colorBackground: "#ffffff",
        colorText: "#1f2937",
        colorTextSecondary: "#4b5563",
        colorTextPlaceholder: "#6b7280",
        colorDanger: "#b42318",
        fontFamily: "Sora, sans-serif",
        borderRadius: "8px",
    },
    rules: {
        ".Label": {
            color: "#9fb0cc",
            fontSize: "13px",
            fontWeight: "600",
        },
        ".Tab": {
            backgroundColor: "#ffffff",
            border: "1px solid #d7dce5",
            color: "#1f2937",
        },
        ".Tab:hover": {
            color: "#0e1c3d",
        },
        ".Tab--selected": {
            borderColor: "#2bcc87",
            color: "#0e1c3d",
        },
        ".TabLabel": {
            color: "#1f2937",
        },
        ".Input": {
            backgroundColor: "#ffffff",
            borderColor: "#d7dce5",
            color: "#1f2937",
        },
        ".Input::placeholder": {
            color: "#6b7280",
        },
        ".Block": {
            backgroundColor: "#ffffff",
            color: "#1f2937",
        },
        ".BlockLabel": {
            color: "#1f2937",
        },
        ".AccordionItem": {
            backgroundColor: "#ffffff",
            color: "#1f2937",
        },
        ".AccordionItemContent": {
            color: "#1f2937",
        },
        ".PickerItem": {
            color: "#1f2937",
        },
        ".PickerItemLabel": {
            color: "#1f2937",
        },
        ".Text": {
            color: "#1f2937",
        },
        ".RedirectText": {
            color: "#1f2937",
        },
        ".TermsText": {
            color: "#1f2937",
        },
        ".LinkLegal": {
            color: "#1f2937",
        },
    },
};

function isPlausibleBillingAddress(address) {
    const value = address.trim().toLowerCase();
    const hasStreetNumber = /\d/.test(value);
    const hasLetters = /[a-z]{3,}/.test(value);
    const hasStreetType = /\b(st|street|rd|road|ave|avenue|dr|drive|ln|lane|ct|court|cres|crescent|way|pde|parade|pl|place|blvd|boulevard)\b/.test(value);
    const hasAreaSeparator = /,/.test(value) || /\b(vic|nsw|qld|sa|wa|tas|act|nt)\b/.test(value) || /\b\d{4}\b/.test(value);

    return value.length >= 10 && hasStreetNumber && hasLetters && hasStreetType && hasAreaSeparator;
}

addressInput.addEventListener("input", function () {
    addressInput.setCustomValidity("");
});

detailsForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (!detailsForm.checkValidity()) {
        detailsForm.reportValidity();
        return;
    }

    if (!isPlausibleBillingAddress(addressInput.value)) {
        addressInput.setCustomValidity("Enter a real billing address with a street number, street name, and suburb/state or postcode.");
        addressInput.reportValidity();
        return;
    }

    continueButton.disabled = true;
    continueButton.innerText = "Loading payment...";

    const formData = new FormData(detailsForm);

    const response = await fetch("/create-payment-intent", {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    if (!response.ok || data.error) {
        paymentMessage.innerText = data.error || "Something went wrong.";
        continueButton.disabled = false;
        continueButton.innerText = "Continue to Payment →";
        return;
    }

    elements = stripe.elements({
        clientSecret: data.client_secret,
        appearance: paymentAppearance
    });
    const paymentElement = elements.create("payment");
    paymentElement.mount("#payment-element");

    paymentCardLocked.classList.add("hidden");
    paymentElementWrapper.classList.remove("hidden");

    continueButton.disabled = false;
    continueButton.innerText = "Details Saved ✓";
    continueButton.disabled = true;
});

payButton.addEventListener("click", async function () {
    payButton.disabled = true;
    payButton.innerText = "Processing...";

    const { error } = await stripe.confirmPayment({
        elements,
        confirmParams: {
            return_url: `${window.location.origin}/payment_success`
        }
    });

    if (error) {
        paymentMessage.innerText = error.message;
        payButton.disabled = false;
        payButton.innerText = "Pay Now";
    }
});
