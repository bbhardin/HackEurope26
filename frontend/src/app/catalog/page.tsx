"use client";

import { useEffect, useState, useMemo } from "react";
import { getAllProducts, createProduct, updateProduct, deleteProduct } from "@/lib/api";
import type { Product, CreateProductInput } from "@/lib/types";

export default function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editPrice, setEditPrice] = useState(0);
  const [newProduct, setNewProduct] = useState<CreateProductInput>({ name: "", sku: "", category: "", unit: "kg", unit_type: "continuous", price_default: 0 });

  const loadProducts = () => {
    getAllProducts().then(setProducts).catch(console.error);
  };

  useEffect(() => { loadProducts(); }, []);

  const categories = useMemo(() => {
    const cats = new Set(products.map((p) => p.category));
    return Array.from(cats).sort();
  }, [products]);

  const filtered = useMemo(() => {
    let result = products;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter((p) => p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q));
    }
    if (categoryFilter) {
      result = result.filter((p) => p.category === categoryFilter);
    }
    return result;
  }, [products, search, categoryFilter]);

  const handleCreate = async () => {
    if (!newProduct.name || !newProduct.sku) return;
    try {
      await createProduct(newProduct);
      setNewProduct({ name: "", sku: "", category: "", unit: "kg", unit_type: "continuous", price_default: 0 });
      setShowAdd(false);
      loadProducts();
    } catch (e) {
      console.error("Failed to create product:", e);
    }
  };

  const handleUpdate = async (id: string) => {
    try {
      await updateProduct(id, editName, editPrice);
      setEditingId(null);
      loadProducts();
    } catch (e) {
      console.error("Failed to update product:", e);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteProduct(id);
      loadProducts();
    } catch (e) {
      console.error("Failed to delete product:", e);
    }
  };

  const startEdit = (p: Product) => {
    setEditingId(p.id);
    setEditName(p.name);
    setEditPrice(p.price_default);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Product Catalog</h2>
        <button onClick={() => setShowAdd(!showAdd)} className="px-4 py-2 rounded text-sm font-medium cursor-pointer" style={{ background: "var(--color-accent)", color: "#fff" }}>
          {showAdd ? "Cancel" : "Add Product"}
        </button>
      </div>

      {showAdd && (
        <div className="rounded-lg border p-4 mb-6" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <input placeholder="Product name" value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
            <input placeholder="SKU" value={newProduct.sku} onChange={(e) => setNewProduct({ ...newProduct, sku: e.target.value })} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
            <input placeholder="Category" value={newProduct.category} onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
          </div>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <select value={newProduct.unit} onChange={(e) => setNewProduct({ ...newProduct, unit: e.target.value })} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)", color: "var(--color-text)" }}>
              {["kg", "L", "pc", "bottle", "bag", "box", "tray", "can", "jar", "bunch", "tub", "pack", "bucket"].map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
            <select value={newProduct.unit_type} onChange={(e) => setNewProduct({ ...newProduct, unit_type: e.target.value })} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)", color: "var(--color-text)" }}>
              <option value="continuous">Continuous</option>
              <option value="discrete">Discrete</option>
            </select>
            <input type="number" placeholder="Price" value={newProduct.price_default || ""} onChange={(e) => setNewProduct({ ...newProduct, price_default: parseFloat(e.target.value) || 0 })} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
          </div>
          <button onClick={handleCreate} className="px-4 py-2 rounded text-sm font-medium cursor-pointer" style={{ background: "var(--color-green)", color: "#fff" }}>Create Product</button>
        </div>
      )}

      <div className="flex items-center gap-3 mb-4">
        <input placeholder="Search by name or SKU..." value={search} onChange={(e) => setSearch(e.target.value)} className="px-3 py-2 rounded border text-sm w-64" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)", color: "var(--color-text)" }}>
          <option value="">All categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
        <span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>{filtered.length} products</span>
      </div>

      <div className="rounded-lg border overflow-hidden" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ color: "var(--color-text-muted)" }}>
              <th className="text-left text-xs font-medium px-4 py-3">Name</th>
              <th className="text-left text-xs font-medium px-4 py-3">SKU</th>
              <th className="text-left text-xs font-medium px-4 py-3">Category</th>
              <th className="text-left text-xs font-medium px-4 py-3">Unit</th>
              <th className="text-right text-xs font-medium px-4 py-3">Price (EUR)</th>
              <th className="text-right text-xs font-medium px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((product) => (
              <tr key={product.id} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                <td className="px-4 py-2.5">
                  {editingId === product.id ? (
                    <input value={editName} onChange={(e) => setEditName(e.target.value)} className="px-2 py-1 rounded border text-sm w-full" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
                  ) : (
                    <span className="font-medium">{product.name}</span>
                  )}
                </td>
                <td className="px-4 py-2.5 font-mono text-xs" style={{ color: "var(--color-text-muted)" }}>{product.sku}</td>
                <td className="px-4 py-2.5 text-xs">
                  <span className="px-2 py-0.5 rounded" style={{ background: "rgba(79,140,255,0.1)", color: "var(--color-accent)" }}>{product.category}</span>
                </td>
                <td className="px-4 py-2.5 text-xs">{product.unit} ({product.unit_type})</td>
                <td className="px-4 py-2.5 text-right">
                  {editingId === product.id ? (
                    <input type="number" value={editPrice} onChange={(e) => setEditPrice(parseFloat(e.target.value) || 0)} className="px-2 py-1 rounded border text-sm w-20 text-right" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
                  ) : (
                    <span>{product.price_default.toFixed(2)}</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right">
                  {editingId === product.id ? (
                    <div className="flex gap-1 justify-end">
                      <button onClick={() => handleUpdate(product.id)} className="text-xs px-2 py-1 rounded cursor-pointer" style={{ background: "var(--color-green)", color: "#fff" }}>Save</button>
                      <button onClick={() => setEditingId(null)} className="text-xs px-2 py-1 rounded cursor-pointer border" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>Cancel</button>
                    </div>
                  ) : (
                    <div className="flex gap-1 justify-end">
                      <button onClick={() => startEdit(product)} className="text-xs px-2 py-1 rounded cursor-pointer border" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>Edit</button>
                      <button onClick={() => handleDelete(product.id)} className="text-xs px-2 py-1 rounded cursor-pointer" style={{ color: "var(--color-red)" }}>Delete</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="p-8 text-sm text-center" style={{ color: "var(--color-text-muted)" }}>No products match your search</p>
        )}
      </div>
    </div>
  );
}
