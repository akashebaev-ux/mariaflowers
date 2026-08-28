/* jshint esversion: 6 */

document.addEventListener("DOMContentLoaded", function () {
    const messageField = document.getElementById(
        "id_greeting_message"
    );

    const counter = document.getElementById(
        "greeting-message-counter"
    );

    const quantityField = document.querySelector(
        ".qty_input"
    );

    const totalElement = document.getElementById(
        "custom-product-total"
    );

    const basePriceField = document.getElementById(
        "base-product-price"
    );

    function updateMessageCounter() {
        if (!messageField || !counter) {
            return;
        }

        counter.textContent =
            `${messageField.value.length} / 250 characters`;
    }

    function updateProductTotal() {
        if (
            !quantityField ||
            !totalElement ||
            !basePriceField
        ) {
            return;
        }

        const productPrice = Number.parseFloat(
            basePriceField.value
        );

        let quantity = Number.parseInt(
            quantityField.value,
            10
        );

        if (Number.isNaN(quantity) || quantity < 1) {
            quantity = 1;
        }

        if (Number.isNaN(productPrice)) {
            return;
        }

        const total = productPrice * quantity;

        totalElement.textContent = `$${total.toFixed(2)}`;
    }

    if (messageField) {
        messageField.addEventListener(
            "input",
            updateMessageCounter
        );

        updateMessageCounter();
    }

    if (quantityField) {
        quantityField.addEventListener(
            "input",
            updateProductTotal
        );

        quantityField.addEventListener(
            "change",
            updateProductTotal
        );

        document.addEventListener("click", function (event) {
            const quantityButton = event.target.closest(
                ".increment-qty, .decrement-qty"
            );

            if (!quantityButton) {
                return;
            }

            window.setTimeout(updateProductTotal, 0);
        });

        updateProductTotal();
    }
});
