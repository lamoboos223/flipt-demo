let currentEnv = window.APP_CONFIG.env;
let currentCity = window.APP_CONFIG.city;
let selectedProduct = null;
let selectedPayment = "credit-card";
let paymentMethods = [];
let allProducts = [];

function renderProducts(products) {
  const list = document.getElementById("product-list");

  if (products.length === 0) {
    list.innerHTML = '<div class="loading">No products match your search</div>';
    return;
  }

  list.innerHTML = products
    .map(
      (p) => `
    <div class="product-card" data-id="${p.id}" data-name="${p.name}" data-price="${p.price}">
      <img src="${p.image_url}" alt="${p.name}" loading="lazy">
      <div class="product-info">
        <span class="product-category">${p.category}</span>
        <span class="product-name">${p.name}</span>
        <span class="product-rating">★ ${p.rating}</span>
        <span class="product-price">$${Number(p.price).toFixed(2)}</span>
        <button class="buy-btn">${window.APP_CONFIG.expressCheckout ? "⚡ Buy Now" : "Buy"}</button>
      </div>
    </div>`
    )
    .join("");

  document.querySelectorAll(".product-card").forEach((card) => {
    card.addEventListener("click", () => openCheckout(card));
  });
}

function filterProducts(query) {
  const term = query.trim().toLowerCase();
  if (!term) {
    renderProducts(allProducts);
    return;
  }

  const filtered = allProducts.filter(
    (p) =>
      p.name.toLowerCase().includes(term) ||
      p.category.toLowerCase().includes(term) ||
      p.description.toLowerCase().includes(term)
  );
  renderProducts(filtered);
}

async function loadProducts() {
  const list = document.getElementById("product-list");
  try {
    const res = await fetch("/api/products");
    const data = await res.json();
    allProducts = data.products;
    renderProducts(allProducts);
  } catch {
    list.innerHTML = '<div class="loading">Failed to load products</div>';
  }
}

async function loadFlags() {
  const res = await fetch(`/api/flags?env=${currentEnv}&city=${encodeURIComponent(currentCity)}`);
  const data = await res.json();
  paymentMethods = data.payment_methods;
  return data;
}

function renderPaymentMethods() {
  const container = document.getElementById("payment-methods");
  container.innerHTML = paymentMethods
    .map(
      (m, i) => `
    <label class="payment-option ${i === 0 ? "selected" : ""}" data-id="${m.id}">
      <input type="radio" name="payment" value="${m.id}" ${i === 0 ? "checked" : ""}>
      <span>${m.icon}</span>
      <span>${m.name}</span>
    </label>`
    )
    .join("");

  selectedPayment = paymentMethods[0]?.id || "credit-card";

  container.querySelectorAll(".payment-option").forEach((opt) => {
    opt.addEventListener("click", () => {
      container.querySelectorAll(".payment-option").forEach((o) => o.classList.remove("selected"));
      opt.classList.add("selected");
      opt.querySelector("input").checked = true;
      selectedPayment = opt.dataset.id;
    });
  });
}

async function openCheckout(card) {
  selectedProduct = {
    id: card.dataset.id,
    name: card.dataset.name,
    price: card.dataset.price,
  };

  await loadFlags();

  document.getElementById("checkout-product").innerHTML = `
    <strong>${selectedProduct.name}</strong><br>
    <span style="color: var(--accent); font-size: 18px; font-weight: 700;">$${Number(selectedProduct.price).toFixed(2)}</span>
  `;

  renderPaymentMethods();
  document.getElementById("order-result").className = "order-result hidden";
  document.getElementById("checkout-modal").classList.remove("hidden");
}

document.getElementById("close-modal").addEventListener("click", () => {
  document.getElementById("checkout-modal").classList.add("hidden");
});

document.getElementById("place-order").addEventListener("click", async () => {
  const resultEl = document.getElementById("order-result");
  const btn = document.getElementById("place-order");
  btn.disabled = true;

  try {
    const res = await fetch(`/api/checkout?env=${currentEnv}&city=${encodeURIComponent(currentCity)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: selectedProduct.id,
        payment_method: selectedPayment,
        city: currentCity,
      }),
    });

    const data = await res.json();

    if (res.ok) {
      resultEl.className = "order-result success";
      resultEl.textContent = `✓ ${data.message} — Order ${data.order_id}`;
    } else {
      resultEl.className = "order-result error";
      resultEl.textContent = `✗ ${data.detail?.message || data.detail || "Checkout failed"}`;
    }
  } catch {
    resultEl.className = "order-result error";
    resultEl.textContent = "✗ Network error during checkout";
  }

  btn.disabled = false;
});

document.querySelectorAll(".env-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    currentEnv = btn.dataset.env;
    window.location.href = `/?env=${currentEnv}&city=${encodeURIComponent(currentCity)}`;
  });
});

document.getElementById("city-select").addEventListener("change", (event) => {
  currentCity = event.target.value;
  window.location.href = `/?env=${currentEnv}&city=${encodeURIComponent(currentCity)}`;
});

document.getElementById("search-input").addEventListener("input", (event) => {
  filterProducts(event.target.value);
});

loadProducts();
