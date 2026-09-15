const apiBase = document.body.dataset.apiBase.replace(/\/$/, "");
const cartKey = "standard-supply.cart.v1";
const productGrid = document.querySelector("#product-grid");
const cartCount = document.querySelector("#cart-count");
const cartStatus = document.querySelector("#cart-status");
const cartDialog = document.querySelector("#cart-dialog");
const cartItems = document.querySelector("#cart-items");
const cartTotal = document.querySelector("#cart-total");
const checkoutForm = document.querySelector("#checkout-form");
const checkoutStatus = document.querySelector("#checkout-status");
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const products = new Map();
let activeFilter = "all";
let cart = loadCart();

function loadCart() {
  try {
    const saved = JSON.parse(localStorage.getItem(cartKey) || "[]");
    return new Map(saved.filter(([slug, quantity]) => typeof slug === "string" && Number.isInteger(quantity) && quantity > 0));
  } catch {
    return new Map();
  }
}

function saveCart() {
  localStorage.setItem(cartKey, JSON.stringify([...cart]));
}

function formatMoney(cents) {
  return money.format(cents / 100);
}

function imageClass(slug) {
  return { "day-bottle": "image-bottle", "market-tote": "image-tote", "after-rain": "image-candle" }[slug] || "";
}

async function api(path, options = {}) {
  if (!apiBase) throw new Error("The store API has not been configured.");
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: { Accept: "application/json", ...options.headers },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "The request could not be completed.");
  return payload;
}

function createProduct(product) {
  const article = document.createElement("article");
  article.className = "product";
  article.dataset.category = product.category;
  article.hidden = activeFilter !== "all" && product.category !== activeFilter;
  const image = document.createElement("div");
  image.className = `product-image ${imageClass(product.slug)}`;
  const imageElement = document.createElement("img");
  imageElement.src = "assets/standard-supply-products.png";
  imageElement.alt = product.name;
  image.append(imageElement);
  const meta = document.createElement("div");
  meta.className = "product-meta";
  const description = document.createElement("div");
  const name = document.createElement("h3");
  name.textContent = product.name;
  const details = document.createElement("p");
  details.textContent = product.description;
  description.append(name, details);
  const price = document.createElement("strong");
  price.textContent = formatMoney(product.price_cents);
  meta.append(description, price);
  const button = document.createElement("button");
  button.className = "add-button";
  button.type = "button";
  button.dataset.product = product.slug;
  button.disabled = product.inventory < 1;
  button.innerHTML = product.inventory < 1 ? "Sold out" : "Add to bag <span>+</span>";
  article.append(image, meta, button);
  return article;
}

function renderProducts() {
  productGrid.replaceChildren();
  [...products.values()].forEach((product) => productGrid.append(createProduct(product)));
}

function cartLines() {
  return [...cart].map(([slug, quantity]) => ({ product: products.get(slug), quantity })).filter(({ product }) => product);
}

function renderCart() {
  const lines = cartLines();
  const itemCount = lines.reduce((total, line) => total + line.quantity, 0);
  const subtotal = lines.reduce((total, line) => total + line.product.price_cents * line.quantity, 0);
  cartCount.textContent = String(itemCount);
  cartTotal.textContent = formatMoney(subtotal);
  cartItems.replaceChildren();
  if (!lines.length) {
    const empty = document.createElement("p");
    empty.className = "cart-empty";
    empty.textContent = "Your bag is empty. Add something useful from the collection.";
    cartItems.append(empty);
    cartStatus.textContent = "Your bag is empty.";
    return;
  }
  lines.forEach(({ product, quantity }) => {
    const row = document.createElement("div");
    row.className = "cart-line";
    const label = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = product.name;
    const detail = document.createElement("span");
    detail.textContent = `${formatMoney(product.price_cents)} each`;
    label.append(title, detail);
    const controls = document.createElement("div");
    controls.className = "quantity-controls";
    controls.append(quantityButton("−", product.slug, "decrease"));
    const quantityLabel = document.createElement("span");
    quantityLabel.textContent = String(quantity);
    controls.append(quantityLabel, quantityButton("+", product.slug, "increase"));
    const total = document.createElement("strong");
    total.textContent = formatMoney(product.price_cents * quantity);
    row.append(label, controls, total);
    cartItems.append(row);
  });
  cartStatus.textContent = `${itemCount} item${itemCount === 1 ? "" : "s"} in your bag. Subtotal ${formatMoney(subtotal)}.`;
}

function quantityButton(label, slug, action) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "quantity-button";
  button.dataset.slug = slug;
  button.dataset.action = action;
  button.textContent = label;
  button.setAttribute("aria-label", `${action} ${products.get(slug)?.name || "item"}`);
  return button;
}

function changeQuantity(slug, change) {
  const product = products.get(slug);
  if (!product) return;
  const next = Math.min(10, product.inventory, (cart.get(slug) || 0) + change);
  if (next <= 0) cart.delete(slug);
  else cart.set(slug, next);
  saveCart();
  renderCart();
}

async function loadProducts() {
  try {
    const payload = await api("/api/products");
    payload.products.forEach((product) => products.set(product.slug, product));
    for (const slug of cart.keys()) if (!products.has(slug)) cart.delete(slug);
    saveCart();
    renderProducts();
    renderCart();
  } catch (error) {
    productGrid.replaceChildren();
    const state = document.createElement("p");
    state.className = "catalog-state is-error";
    state.textContent = `The collection is unavailable right now. ${error.message}`;
    productGrid.append(state);
    cartStatus.textContent = "The bag will be available when the catalog reconnects.";
  }
}

document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    document.querySelectorAll(".filter").forEach((item) => item.classList.toggle("is-active", item === button));
    renderProducts();
  });
});

productGrid.addEventListener("click", (event) => {
  const button = event.target.closest(".add-button");
  if (!button || button.disabled) return;
  changeQuantity(button.dataset.product, 1);
  cartStatus.textContent = `${products.get(button.dataset.product).name} added to your bag.`;
});

cartItems.addEventListener("click", (event) => {
  const button = event.target.closest(".quantity-button");
  if (button) changeQuantity(button.dataset.slug, button.dataset.action === "increase" ? 1 : -1);
});

document.querySelector(".cart-button").addEventListener("click", () => cartDialog.showModal());
document.querySelector(".close-cart").addEventListener("click", () => cartDialog.close());
cartDialog.addEventListener("click", (event) => {
  if (event.target === cartDialog) cartDialog.close();
});

checkoutForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const lines = cartLines();
  if (!lines.length) {
    checkoutStatus.textContent = "Add an item before submitting an order.";
    return;
  }
  const submit = checkoutForm.querySelector("button[type=submit]");
  submit.disabled = true;
  checkoutStatus.textContent = "Submitting your order…";
  try {
    const form = new FormData(checkoutForm);
    const payload = await api("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: form.get("email"), items: lines.map(({ product, quantity }) => ({ slug: product.slug, quantity })) }),
    });
    cart = new Map();
    saveCart();
    renderCart();
    checkoutForm.reset();
    checkoutStatus.textContent = `Order ${payload.order.id} received. Payment has not been collected.`;
  } catch (error) {
    checkoutStatus.textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});

renderCart();
loadProducts();
