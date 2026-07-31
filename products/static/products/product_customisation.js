document.addEventListener("DOMContentLoaded", function () {
    const extraFlowersInput = document.getElementById(
        "id_extra_flowers"
    );

    if (!extraFlowersInput) {
        return;
    }

    const quantityInput = document.getElementById(
        document.querySelector(".qty_input").id
    );

    const basePriceInput = document.getElementById(
        "base-product-price"
    );

    const extraFlowerPriceInput = document.getElementById(
        "extra-flower-price"
    );

    const includedFlowerCountInput = document.getElementById(
        "included-flower-count"
    );

    const additionalFlowersTotalDisplay = document.getElementById(
        "additional-flowers-total"
    );

    const totalPriceDisplay = document.getElementById(
        "custom-product-total"
    );

    const totalFlowerCountDisplay = document.getElementById(
        "total-flower-count"
    );

    const incrementExtraButton = document.getElementById(
        "increment-extra-flowers"
    );

    const decrementExtraButton = document.getElementById(
        "decrement-extra-flowers"
    );

    const basePrice =
        parseFloat(basePriceInput.value) || 0;

    const extraFlowerPrice =
        parseFloat(extraFlowerPriceInput.value) || 0;

    const includedFlowerCount =
        parseInt(includedFlowerCountInput.value, 10) || 0;

    function updateCustomisation() {

        const extraFlowers = Math.max(
            0,
            Math.min(
                parseInt(extraFlowersInput.value, 10) || 0,
                parseInt(extraFlowersInput.max, 10)
            )
        );

        const quantity = Math.max(
            1,
            parseInt(quantityInput.value, 10) || 1
        );

        extraFlowersInput.value = extraFlowers;

        const additionalFlowersPrice =
            extraFlowers * extraFlowerPrice;

        const customisedUnitPrice =
            basePrice + additionalFlowersPrice;

        const overallPrice =
            customisedUnitPrice * quantity;

        additionalFlowersTotalDisplay.textContent =
            `$${additionalFlowersPrice.toFixed(2)}`;

        totalPriceDisplay.textContent =
            `$${overallPrice.toFixed(2)}`;

        totalFlowerCountDisplay.textContent =
            includedFlowerCount + extraFlowers;
    }

    incrementExtraButton.addEventListener("click", function () {
        extraFlowersInput.value =
            parseInt(extraFlowersInput.value, 10) + 1;

        updateCustomisation();
    });

    decrementExtraButton.addEventListener("click", function () {
        extraFlowersInput.value = Math.max(
            0,
            parseInt(extraFlowersInput.value, 10) - 1
        );

        updateCustomisation();
    });

    extraFlowersInput.addEventListener(
        "input",
        updateCustomisation
    );

    quantityInput.addEventListener(
        "input",
        updateCustomisation
    );

    document
        .querySelectorAll(".increment-qty, .decrement-qty")
        .forEach(function (button) {
            button.addEventListener("click", function () {
                setTimeout(updateCustomisation, 0);
            });
        });

    updateCustomisation();
});
