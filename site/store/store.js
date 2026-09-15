const cart = [];
const cartCount = document.querySelector("#cart-count");
const cartStatus = document.querySelector("#cart-status");

document.querySelectorAll(".add-button").forEach((button) => {
  button.addEventListener("click", () => {
    cart.push(button.dataset.product);
    cartCount.textContent = String(cart.length);
    cartStatus.textContent = `${button.dataset.product} added to your demo bag. ${cart.length} item${cart.length === 1 ? "" : "s"} selected.`;
  });
});

document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    document.querySelectorAll(".product").forEach((product) => {
      product.hidden = button.dataset.filter !== "all" && product.dataset.category !== button.dataset.filter;
    });
  });
});
