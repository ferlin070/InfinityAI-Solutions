import React, { useState, useEffect } from 'react';
import { Building2, Package, Plus, Pencil, Trash2, Save, X } from 'lucide-react';
import { fetchBusinessProfile, updateBusinessProfile, fetchProducts, createProduct, updateProduct, deleteProduct } from '../api';

export default function BusinessConfig({ t }) {
  const [profile, setProfile] = useState({
    company_name: '', industry: '', description: '', address: '',
    phone: '', email: '', website: '', logo_url: '',
  });
  const [products, setProducts] = useState([]);
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState(null);
  const [showProductForm, setShowProductForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [productForm, setProductForm] = useState({ name: '', unit_price: '', description: '', stock_qty: '' });
  const [productMsg, setProductMsg] = useState(null);
  const [savingProduct, setSavingProduct] = useState(false);

  useEffect(() => { loadProfile(); loadProducts(); }, []);

  async function loadProfile() {
    try {
      const data = await fetchBusinessProfile();
      if (data) setProfile(data);
    } catch (e) { console.error(e); }
  }

  async function loadProducts() {
    try {
      const data = await fetchProducts() || [];
      setProducts(data);
    } catch (e) { console.error(e); }
  }

  async function handleSaveProfile() {
    setSavingProfile(true);
    setProfileMsg(null);
    try {
      const res = await updateBusinessProfile(profile);
      if (res) setProfileMsg({ type: 'success', text: t('bc-profile-saved') });
    } catch (e) {
      setProfileMsg({ type: 'error', text: 'Gagal menyimpan profil.' });
    } finally {
      setSavingProfile(false);
      setTimeout(() => setProfileMsg(null), 3000);
    }
  }

  function openAddProduct() {
    setEditingProduct(null);
    setProductForm({ name: '', unit_price: '', description: '', stock_qty: '' });
    setShowProductForm(true);
  }

  function openEditProduct(product) {
    setEditingProduct(product);
    setProductForm({
      name: product.name,
      unit_price: String(product.unit_price),
      description: product.description || '',
      stock_qty: product.stock_qty !== null ? String(product.stock_qty) : '',
    });
    setShowProductForm(true);
  }

  async function handleSaveProduct() {
    setSavingProduct(true);
    setProductMsg(null);
    try {
      const payload = {
        name: productForm.name,
        unit_price: parseFloat(productForm.unit_price) || 0,
        description: productForm.description || null,
        stock_qty: productForm.stock_qty !== '' ? parseInt(productForm.stock_qty) : null,
      };
      if (editingProduct) {
        await updateProduct(editingProduct.id, payload);
      } else {
        await createProduct(payload);
      }
      setProductMsg({ type: 'success', text: t('bc-product-saved') });
      setShowProductForm(false);
      await loadProducts();
    } catch (e) {
      setProductMsg({ type: 'error', text: 'Gagal menyimpan produk.' });
    } finally {
      setSavingProduct(false);
      setTimeout(() => setProductMsg(null), 3000);
    }
  }

  async function handleDeleteProduct(productId) {
    if (!confirm(t('bc-confirm-delete'))) return;
    try {
      await deleteProduct(productId);
      setProductMsg({ type: 'success', text: t('bc-product-deleted') });
      await loadProducts();
    } catch (e) {
      setProductMsg({ type: 'error', text: 'Gagal memadam produk.' });
    } finally {
      setTimeout(() => setProductMsg(null), 3000);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      {/* Left — Company Profile */}
      <div className="lg:col-span-2 space-y-4">
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center space-x-2">
              <Building2 className="w-4 h-4 text-primary" />
              <div>
                <h3 className="text-base font-semibold">{t('bc-profile')}</h3>
                <p className="text-xs text-text-muted">{t('bc-profile-desc')}</p>
              </div>
            </div>
            <button
              onClick={handleSaveProfile}
              disabled={savingProfile}
              className="btn-primary"
            >
              <Save className="w-3.5 h-3.5 mr-1" />
              {savingProfile ? t('bc-saving') : t('bc-save-profile')}
            </button>
          </div>

          {profileMsg && (
            <div className={`p-2.5 rounded text-xs flex items-center ${
              profileMsg.type === 'success' 
                ? 'bg-accent-success/10 text-accent-success' 
                : 'bg-accent-danger/10 text-accent-danger'
            }`}>
              {profileMsg.type === 'success' ? '✓' : '✗'} {profileMsg.text}
            </div>
          )}

          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-text-muted">{t('bc-company-name')}</label>
                <input type="text" value={profile.company_name}
                  onChange={(e) => setProfile({ ...profile, company_name: e.target.value })}
                  className="input-field" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-text-muted">{t('bc-industry')}</label>
                <input type="text" value={profile.industry} placeholder={t('bc-industry-placeholder')}
                  onChange={(e) => setProfile({ ...profile, industry: e.target.value })}
                  className="input-field" />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-text-muted">{t('bc-description')}</label>
              <textarea value={profile.description} placeholder={t('bc-description-placeholder')}
                onChange={(e) => setProfile({ ...profile, description: e.target.value })}
                rows={4}
                className="w-full bg-background border border-border focus:border-primary/50 outline-none p-2 rounded text-xs leading-relaxed" />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-text-muted">{t('bc-address')}</label>
              <input type="text" value={profile.address}
                onChange={(e) => setProfile({ ...profile, address: e.target.value })}
                className="input-field" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-text-muted">{t('bc-phone')}</label>
                <input type="text" value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  className="input-field" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-text-muted">{t('bc-email')}</label>
                <input type="email" value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                  className="input-field" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-text-muted">{t('bc-website')}</label>
                <input type="text" value={profile.website}
                  onChange={(e) => setProfile({ ...profile, website: e.target.value })}
                  className="input-field" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-text-muted">{t('bc-logo-url')}</label>
                <input type="text" value={profile.logo_url}
                  onChange={(e) => setProfile({ ...profile, logo_url: e.target.value })}
                  className="input-field" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right — Product Catalog */}
      <div className="lg:col-span-3 space-y-4">
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center space-x-2">
              <Package className="w-4 h-4 text-primary" />
              <div>
                <h3 className="text-base font-semibold">{t('bc-products')}</h3>
                <p className="text-xs text-text-muted">{t('bc-products-desc')}</p>
              </div>
            </div>
            {!showProductForm && (
              <button onClick={openAddProduct}
                className="btn-primary">
                <Plus className="w-3.5 h-3.5 mr-1" />
                {t('bc-add-product')}
              </button>
            )}
          </div>

          {productMsg && (
            <div className={`p-2.5 rounded text-xs flex items-center ${
              productMsg.type === 'success' 
                ? 'bg-accent-success/10 text-accent-success' 
                : 'bg-accent-danger/10 text-accent-danger'
            }`}>
              {productMsg.type === 'success' ? '✓' : '✗'} {productMsg.text}
            </div>
          )}

          {showProductForm && (
            <div className="p-4 bg-surface-raised border border-border rounded-lg space-y-3">
              <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider">
                {editingProduct ? t('bc-edit-product') : t('bc-add-product')}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-text-muted">{t('bc-product-name')}</label>
                  <input type="text" value={productForm.name}
                    onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                    className="input-field" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-text-muted">{t('bc-product-price')}</label>
                  <input type="number" step="0.01" min="0" value={productForm.unit_price}
                    onChange={(e) => setProductForm({ ...productForm, unit_price: e.target.value })}
                    className="input-field" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-text-muted">{t('bc-product-desc')}</label>
                  <input type="text" value={productForm.description}
                    onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
                    className="input-field" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-text-muted">{t('bc-product-stock')}</label>
                  <input type="number" min="0" value={productForm.stock_qty}
                    onChange={(e) => setProductForm({ ...productForm, stock_qty: e.target.value })}
                    className="input-field" />
                </div>
              </div>
              <div className="flex space-x-2 pt-1">
                <button onClick={handleSaveProduct} disabled={savingProduct || !productForm.name}
                  className="btn-primary">
                  <Save className="w-3.5 h-3.5 mr-1" />
                  {savingProduct ? t('bc-saving') : t('bc-product-save')}
                </button>
                <button onClick={() => setShowProductForm(false)}
                  className="flex items-center text-xs text-text-muted hover:text-text border border-border px-3 py-1.5 rounded-lg transition-all hover:bg-surface-raised">
                  <X className="w-3.5 h-3.5 mr-1" />
                  {t('bc-product-cancel')}
                </button>
              </div>
            </div>
          )}

          {products.length === 0 ? (
            <div className="p-6 text-center text-xs text-text-muted bg-surface rounded-lg">
              {t('bc-no-products')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border text-text-muted font-semibold text-[10px] uppercase tracking-wider">
                    <th className="text-left p-2">{t('bc-product-name')}</th>
                    <th className="text-left p-2">{t('bc-product-desc')}</th>
                    <th className="text-right p-2">{t('bc-product-price')}</th>
                    <th className="text-right p-2">{t('bc-product-stock')}</th>
                    <th className="text-right p-2 w-20">Tindakan</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id} className="border-b border-border/50 hover:bg-surface-raised transition-colors">
                      <td className="p-2 font-semibold">{p.name}</td>
                      <td className="p-2 text-text-muted">{p.description || '-'}</td>
                      <td className="p-2 text-right font-mono">RM {parseFloat(p.unit_price).toFixed(2)}</td>
                      <td className="p-2 text-right">{p.stock_qty !== null ? p.stock_qty : '-'}</td>
                      <td className="p-2 text-right">
                        <div className="flex justify-end space-x-1">
                          <button onClick={() => openEditProduct(p)}
                            className="p-1.5 rounded hover:bg-surface-raised text-text-muted hover:text-primary transition-all">
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => handleDeleteProduct(p.id)}
                            className="p-1.5 rounded hover:bg-surface-raised text-text-muted hover:text-accent-danger transition-all">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}