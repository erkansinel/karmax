// Karmax tarayıcı katmanı.
// KURAL: Burada finansal hesaplama YAPILMAZ. Bu dosya yalnızca
//   1) formlardaki değerleri API'ye gönderir,
//   2) Python'dan dönen sonuçları biçimlendirip gösterir,
//   3) Python'un hazırladığı Plotly grafiklerini çizer.
"use strict";

const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------ biçimlendirme
const bicim = (ondalik) => new Intl.NumberFormat("tr-TR", { minimumFractionDigits: ondalik, maximumFractionDigits: ondalik });
const B2 = bicim(2), B0 = bicim(0), B1 = bicim(1);
const yuzdeBicim = new Intl.NumberFormat("tr-TR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });
const yuzdeBicim2 = new Intl.NumberFormat("tr-TR", { style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const tl = (v, ondalik = 2) => (ondalik === 0 ? B0 : B2).format(v) + " TL";
const isaretli = (v, ondalik = 2) =>
  (v > 0.004 ? "+" : v < -0.004 ? "−" : "") + (ondalik === 0 ? B0 : B2).format(Math.abs(v)) + " TL";
const renk = (v) => (v < -0.004 ? "neg" : v > 0.004 ? "poz" : "");
const yuzde = (oran) => yuzdeBicim.format(oran);
const kacis = (m) => String(m ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const vadeMetni = (s) =>
  s.maksimum_vade_durumu === "sinirli" ? B1.format(s.maksimum_vade_gun) + " gün"
  : s.maksimum_vade_durumu === "sinirsiz" ? "Sınırsız (faiz sıfır)" : "Peşin satışta bile zarar";

// ----------------------------------------------------------- yardımcılar
function sayiOku(deger) {
  const ham = String(deger ?? "").trim().replace(/\s/g, "").replace(",", ".");
  return ham === "" ? null : Number(ham);
}
const sayi = (id) => sayiOku($(id).value);

function hataMetni(veri, durum) {
  if (Array.isArray(veri?.detail)) return veri.detail.map((d) => d.mesaj || d.msg).join(" · ");
  if (typeof veri?.detail === "string") return veri.detail;
  return `Sunucu isteği işleyemedi (kod ${durum}).`;
}

async function gonder(url, govde, sinyal) {
  const secenek = { method: "POST", signal: sinyal };
  if (govde instanceof FormData) secenek.body = govde;
  else { secenek.headers = { "Content-Type": "application/json" }; secenek.body = JSON.stringify(govde); }
  let yanit;
  try { yanit = await fetch(url, secenek); }
  catch (e) {
    if (e.name === "AbortError") throw e;
    throw new Error("Hesap motoruna ulaşılamadı. Karmax penceresinin açık olduğundan emin olun.");
  }
  const veri = await yanit.json().catch(() => ({}));
  if (!yanit.ok) throw new Error(hataMetni(veri, yanit.status));
  return veri;
}

function hataGoster(id, mesaj) { const el = $(id); el.textContent = mesaj || ""; el.hidden = !mesaj; }

async function calistir(dugme, hataId, is) {
  hataGoster(hataId, "");
  if (dugme) dugme.disabled = true;
  try { await is(); }
  catch (e) { if (e.name !== "AbortError") hataGoster(hataId, e.message); }
  finally { if (dugme) dugme.disabled = false; }
}

function ciz(id, fig) {
  if (!fig || !window.Plotly) return;
  Plotly.react(id, fig.data, fig.layout, {
    responsive: true, displaylogo: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines"],
  });
}

const parametreler = () => ({
  yillik_oran_yuzde: sayi("yillik_oran_yuzde"),
  faiz_yontemi: $("faiz_yontemi").value,
  gun_esasi: Number($("gun_esasi").value),
  bilesik_donem: sayi("bilesik_donem"),
});

function varsayimYaz(id, liste) { $(id).innerHTML = (liste || []).map((v) => `<li>${kacis(v)}</li>`).join(""); }

// ---------------------------------------------------------------- sekmeler
const sekmeler = [...document.querySelectorAll('[role="tab"]')];
function sekmeAc(sekme) {
  sekmeler.forEach((s) => {
    const secili = s === sekme;
    s.setAttribute("aria-selected", String(secili));
    s.tabIndex = secili ? 0 : -1;
    $(s.getAttribute("aria-controls")).hidden = !secili;
  });
  // Gizliyken çizilen grafikler doğru genişliği alsın
  $(sekme.getAttribute("aria-controls")).querySelectorAll(".js-plotly-plot").forEach((g) => Plotly.Plots.resize(g));
  try { history.replaceState(null, "", "#" + sekme.id.slice(2)); } catch { /* yok say */ }
}
sekmeler.forEach((s, i) => {
  s.addEventListener("click", () => sekmeAc(s));
  s.addEventListener("keydown", (e) => {
    const y = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (y) { const h = sekmeler[(i + y + sekmeler.length) % sekmeler.length]; sekmeAc(h); h.focus(); }
  });
});

// ============================================================ ÜRÜN ANALİZİ
const URUN_METIN = ["urun_kodu", "urun_adi"];
const URUN_SAYI = ["ilk_alis_maliyeti", "yerine_koyma_maliyeti", "satis_fiyati", "satis_miktari",
  "tahsilat_vadesi_gun", "tedarikci_vadesi_gun", "ek_gider_birim", "hedef_kar_orani_yuzde"];

function urunGirdisi() {
  const u = {};
  URUN_METIN.forEach((k) => (u[k] = $(k).value));
  URUN_SAYI.forEach((k) => (u[k] = sayi(k)));
  return u;
}

function urunGoster(veri, kaydedildi) {
  const s = veri.sonuc;
  $("o-brut").textContent = isaretli(s.muhasebe_brut_kari);
  $("o-brut-dip").textContent =
    `Maliyet üzerinden ${yuzde(s.kar_orani_maliyet_uzerinden)} · satış üzerinden marj ${yuzde(s.brut_kar_marji_satis_uzerinden)}`;
  $("o-yk").textContent = isaretli(s.yerine_koyma_kari);
  $("o-eko").textContent = isaretli(s.ekonomik_sonuc);
  $("o-eko").className = "deger " + renk(s.ekonomik_sonuc);
  const rozet = $("o-rozet");
  rozet.className = "rozet " + (s.ekonomik_sonuc < 0 ? "kayip" : "kazanc");
  rozet.textContent = s.ekonomik_sonuc < 0 ? "▼ Bu satış ekonomik olarak zarar" : "▲ Bu satış ekonomik olarak kârlı";
  $("k-basabas").textContent = tl(s.basabas_satis_fiyati);
  $("k-hedef").textContent = tl(s.hedef_satis_fiyati);
  $("k-vade").textContent = vadeMetni(s);
  $("k-toplam").textContent = isaretli(s.toplam_ekonomik_sonuc);
  $("k-toplam").className = renk(s.toplam_ekonomik_sonuc);

  const satirlar = s.kopru.map((a) =>
    `<tr><td>${kacis(a.ad)}</td><td>${kacis(a.aciklama)}</td><td class="sag ${renk(a.tutar)}">${isaretli(a.tutar)}</td></tr>`);
  satirlar.push(`<tr class="toplam"><td>Ekonomik sonuç</td><td>Tahsilatın bugünkü değeri − maliyetin bugünkü değeri</td>` +
    `<td class="sag ${renk(s.ekonomik_sonuc)}">${isaretli(s.ekonomik_sonuc)}</td></tr>`);
  $("kopru").innerHTML = satirlar.join("");
  varsayimYaz("u-varsayimlar", s.varsayimlar);

  ["u-sonuc", "u-grafikler", "u-detay"].forEach((id) => ($(id).hidden = false));
  ciz("g-selale", veri.grafikler.selale);
  ciz("g-vade", veri.grafikler.vade);
  ciz("g-fiyat", veri.grafikler.fiyat);
  $("u-durum").textContent = kaydedildi
    ? `Kaydedildi · analiz no ${veri.kayit_id} · motor v${s.motor_surumu}`
    : "Önizleme · kaydedilmedi";
}

let onizlemeZamanlayici = null, onizlemeIptal = null;
function onizlemeIste() {
  clearTimeout(onizlemeZamanlayici);
  onizlemeZamanlayici = setTimeout(async () => {
    onizlemeIptal?.abort();
    onizlemeIptal = new AbortController();
    await calistir(null, "u-hata", async () => {
      const veri = await gonder("/api/onizleme", { parametreler: parametreler(), urun: urunGirdisi() }, onizlemeIptal.signal);
      urunGoster(veri, false);
    });
  }, 220);
}

$("form-urun").addEventListener("submit", (e) => {
  e.preventDefault();
  clearTimeout(onizlemeZamanlayici);
  onizlemeIptal?.abort();
  calistir(e.submitter, "u-hata", async () => {
    urunGoster(await gonder("/api/urun-analizi", { parametreler: parametreler(), urun: urunGirdisi() }), true);
  });
});

// Kaydırma çubukları: yalnızca giriş kutularının değerini değiştirir
const cubuklar = [
  { cubuk: "c-fiyat", etiket: "c-fiyat-deger", bicim: (v) => tl(v) },
  { cubuk: "c-vade", etiket: "c-vade-deger", bicim: (v) => B0.format(v) + " gün" },
  { cubuk: "c-oran", etiket: "c-oran-deger", bicim: (v) => "%" + B1.format(v) },
];
function cubukEtiketleri() {
  cubuklar.forEach((c) => {
    const hedef = sayi($(c.cubuk).dataset.hedef);
    $(c.etiket).textContent = hedef === null || Number.isNaN(hedef) ? "—" : c.bicim(hedef);
  });
}
function cubukAraliklari() {
  // Görsel aralık ayarı: çubuğun ucu mevcut değerin yarısı ile 1,5 katı arası
  const f = sayi("satis_fiyati");
  if (f > 0) {
    const c = $("c-fiyat");
    c.min = Math.max(0.5, Math.floor(f * 0.5));
    c.max = Math.ceil(f * 1.5);
    c.step = f >= 1000 ? 1 : 0.5;
    c.value = f;
  }
  const v = sayi("tahsilat_vadesi_gun");
  if (v !== null) { $("c-vade").max = Math.max(365, v); $("c-vade").value = v; }
  const o = sayi("yillik_oran_yuzde");
  if (o !== null) { $("c-oran").max = Math.max(100, o); $("c-oran").value = o; }
  cubukEtiketleri();
}
cubuklar.forEach((c) => {
  $(c.cubuk).addEventListener("input", (e) => {
    $(e.target.dataset.hedef).value = e.target.value;
    cubukEtiketleri();
    onizlemeIste();
  });
});
[...URUN_METIN, ...URUN_SAYI].forEach((id) => {
  $(id).addEventListener("input", () => { cubukEtiketleri(); onizlemeIste(); });
  $(id).addEventListener("change", cubukAraliklari);
});
["yillik_oran_yuzde", "faiz_yontemi", "gun_esasi", "bilesik_donem"].forEach((id) => {
  $(id).addEventListener("input", () => { cubukEtiketleri(); onizlemeIste(); });
  $(id).addEventListener("change", cubukAraliklari);
});

// ============================================================ TOPLU ANALİZ
$("form-toplu").addEventListener("submit", (e) => {
  e.preventDefault();
  calistir(e.submitter, "tp-hata", async () => {
    const dosya = $("dosya").files[0];
    if (!dosya) throw new Error("Önce doldurduğun Excel dosyasını seç.");
    const fd = new FormData();
    fd.append("dosya", dosya);
    topluGoster(await gonder("/api/toplu-analiz", fd));
  });
});

function topluGoster(v) {
  const o = v.ozet;
  $("tp-muhasebe").textContent = isaretli(o.toplam_muhasebe_brut_kari, 0);
  $("tp-urun-sayisi").textContent = `${o.urun_sayisi} ürün · ciro ${tl(o.toplam_ciro, 0)}`;
  $("tp-ekonomik").textContent = isaretli(o.toplam_ekonomik_sonuc, 0);
  $("tp-ekonomik").className = "deger " + renk(o.toplam_ekonomik_sonuc);
  const rozet = $("tp-rozet");
  rozet.className = "rozet " + (o.toplam_ekonomik_sonuc < 0 ? "kayip" : "kazanc");
  rozet.textContent = o.toplam_ekonomik_sonuc < 0 ? "▼ İşletme ekonomik olarak zarar ediyor" : "▲ Ekonomik olarak kârlı";
  $("tp-fark").textContent = tl(o.gizli_fark, 0);
  $("tp-zarar").textContent = `${o.zarar_eden_urun_sayisi} / ${o.urun_sayisi}`;
  $("tp-zarar-dip").textContent = o.zarar_eden_urun_sayisi
    ? `Toplam kayıp ${isaretli(o.zarar_eden_urunlerin_toplam_kaybi, 0)}` : "Zarar eden ürün yok";
  $("tp-indir").href = `/api/toplu-analiz/${v.kayit_id}/excel`;
  const hataliSatir = new Set(v.hatalar.map((h) => h.satir)).size;
  $("tp-durum").textContent = `Analiz no ${v.kayit_id} · ${v.okunan_satir_sayisi} satır okundu · ` +
    `${o.urun_sayisi} ürün hesaplandı · ${hataliSatir} satır hatalı`;

  const uyarilar = [...v.uyarilar];
  if (hataliSatir) uyarilar.unshift(`${hataliSatir} satır hatalı olduğu için hesaplamaya alınmadı. Aşağıdaki listeden düzeltip tekrar yükleyebilirsin.`);
  $("tp-uyarilar").innerHTML = uyarilar.map((u) => `<p class="uyari">${kacis(u)}</p>`).join("");

  $("tp-tablo").innerHTML = v.sonuclar.map((s) => `<tr>
      <td>${kacis(s.urun_kodu)}${s.urun_adi ? " · " + kacis(s.urun_adi) : ""}</td>
      <td class="sag">${B2.format(s.satis_miktari)}</td>
      <td class="sag">${isaretli(s.toplam_muhasebe_brut_kari)}</td>
      <td class="sag ${renk(s.toplam_ekonomik_sonuc)}">${isaretli(s.toplam_ekonomik_sonuc)}</td>
      <td class="sag">${tl(s.basabas_satis_fiyati)}</td>
      <td class="sag">${vadeMetni(s)}</td></tr>`).join("") ||
    `<tr><td colspan="6">Hesaplanabilen ürün yok.</td></tr>`;
  $("tp-hatalar-blok").hidden = v.hatalar.length === 0;
  $("tp-hatalar").innerHTML = v.hatalar.map((h) => `<tr><td>${h.satir}</td><td>${kacis(h.urun_kodu)}</td>` +
    `<td>${kacis(h.mesaj)}</td><td>${kacis(h.deger)}</td></tr>`).join("");
  $("tp-sonuc").hidden = false;
  if (v.grafik) ciz("g-karsilastirma", v.grafik);
  $("g-karsilastirma").parentElement.hidden = !v.grafik;
}

// ======================================================== FİYAT SENARYOLARI
function senaryoSatiri(ad = "", fiyat = "", vade = "") {
  const tr = document.createElement("tr");
  tr.innerHTML = `<td><input class="fs-ad" value="${kacis(ad)}" aria-label="Senaryo adı"></td>
    <td><input class="fs-fiyat" type="number" step="any" value="${kacis(fiyat)}" aria-label="Satış fiyatı"></td>
    <td><input class="fs-vade" type="number" step="1" value="${kacis(vade)}" aria-label="Tahsilat vadesi"></td>
    <td><button type="button" class="sil" aria-label="Senaryoyu sil">Sil</button></td>`;
  tr.querySelector(".sil").addEventListener("click", () => tr.remove());
  $("fs-satirlar").appendChild(tr);
}
function varsayilanSenaryolar() {
  $("fs-satirlar").innerHTML = "";
  const f = $("satis_fiyati").value;
  [["Peşin", 0], ["30 gün", 30], ["60 gün", 60], ["90 gün", 90]].forEach(([ad, g]) => senaryoSatiri(ad, f, g));
}
$("fs-ekle").addEventListener("click", () => senaryoSatiri(`Senaryo ${$("fs-satirlar").rows.length + 1}`, $("satis_fiyati").value, 0));
$("fs-varsayilan").addEventListener("click", varsayilanSenaryolar);

$("form-fiyat").addEventListener("submit", (e) => {
  e.preventDefault();
  calistir(e.submitter, "fs-hata", async () => {
    const senaryolar = [...$("fs-satirlar").rows].map((r) => ({
      ad: r.querySelector(".fs-ad").value.trim(),
      satis_fiyati: sayiOku(r.querySelector(".fs-fiyat").value),
      tahsilat_vadesi_gun: sayiOku(r.querySelector(".fs-vade").value),
    }));
    const v = await gonder("/api/fiyat-senaryolari", {
      parametreler: parametreler(),
      girdi: { urun: urunGirdisi(), senaryolar,
        risk: { odeme_olasiligi_yuzde: sayi("odeme_olasiligi_yuzde"), beklenen_gecikme_gun: sayi("beklenen_gecikme_gun") } },
    });
    const s = v.sonuc;
    const enIyi = s.senaryolar.find((x) => x.ad === s.en_iyi_senaryo);
    $("fs-en-iyi").textContent = `En iyi senaryo: ${s.en_iyi_senaryo} (${isaretli(enIyi.riskli_ekonomik_sonuc)} / birim)`;
    $("fs-en-iyi").className = "vurgu-metin" + (enIyi.riskli_ekonomik_sonuc < 0 ? " kotu" : "");
    $("fs-tablo").innerHTML = s.senaryolar.map((x) => `<tr>
      <td>${kacis(x.ad)}</td><td class="sag">${tl(x.satis_fiyati)}</td><td class="sag">${x.tahsilat_vadesi_gun} gün</td>
      <td class="sag ${renk(x.ekonomik_sonuc)}">${isaretli(x.ekonomik_sonuc)}</td>
      <td class="sag">${tl(x.pesine_esdeger_vadeli_fiyat)}</td><td class="sag">${yuzde(x.gerekli_vade_farki_orani)}</td>
      <td class="sag ${renk(x.riskli_ekonomik_sonuc)}">${isaretli(x.riskli_ekonomik_sonuc)}</td>
      <td class="sag">${tl(x.riskli_basabas_fiyati)}</td></tr>`).join("");
    varsayimYaz("fs-varsayimlar", s.varsayimlar);
    $("fs-durum").textContent = `Kaydedildi · analiz no ${v.kayit_id}`;
    $("fs-sonuc").hidden = false;
    ciz("g-senaryo", v.grafik);
  });
});

// ================================================================== STOK
$("form-stok").addEventListener("submit", (e) => {
  e.preventDefault();
  calistir(e.submitter, "st-hata", async () => {
    const gunler = $("alternatif_stok_gunleri").value.split(/[;,\s]+/).filter(Boolean).map(sayiOku);
    const v = await gonder("/api/stok-analizi", { parametreler: parametreler(), stok: {
      yillik_satilan_mal_maliyeti: sayi("yillik_satilan_mal_maliyeti"),
      ortalama_stok_tutari: sayi("ortalama_stok_tutari"),
      tasima_maliyeti_orani_yuzde: sayi("tasima_maliyeti_orani_yuzde"),
      alternatif_stok_gunleri: gunler,
    } });
    const s = v.sonuc;
    $("st-gun").textContent = B1.format(s.stokta_bekleme_gunu) + " gün";
    $("st-devir").textContent = s.stok_devir_hizi === null ? "—" : B2.format(s.stok_devir_hizi) + " kez / yıl";
    $("st-maliyet").textContent = tl(s.toplam_yillik_maliyet, 0);
    $("st-gunluk").textContent = tl(s.gunluk_stok_maliyeti, 0);
    $("st-tablo").innerHTML = s.senaryolar.map((x) => `<tr${x.mevcut_durum ? ' class="toplam"' : ""}>
      <td>${B1.format(x.stok_gunu)} gün${x.mevcut_durum ? " (mevcut)" : ""}</td>
      <td class="sag">${tl(x.ortalama_stok, 0)}</td><td class="sag">${tl(x.toplam_yillik_maliyet, 0)}</td>
      <td class="sag ${renk(x.mevcuda_gore_yillik_tasarruf)}">${isaretli(x.mevcuda_gore_yillik_tasarruf, 0)}</td>
      <td class="sag ${renk(x.serbest_kalan_nakit)}">${isaretli(x.serbest_kalan_nakit, 0)}</td></tr>`).join("");
    varsayimYaz("st-varsayimlar", s.varsayimlar);
    $("st-durum").textContent = `Kaydedildi · analiz no ${v.kayit_id}`;
    $("st-sonuc").hidden = false;
    ciz("g-stok", v.grafik);
  });
});

function partiSatiri(miktar = "", maliyet = "") {
  const tr = document.createElement("tr");
  tr.innerHTML = `<td><input class="pm-miktar" type="number" step="any" value="${kacis(miktar)}" aria-label="Miktar"></td>
    <td><input class="pm-maliyet" type="number" step="any" value="${kacis(maliyet)}" aria-label="Birim maliyet"></td>
    <td><button type="button" class="sil" aria-label="Partiyi sil">Sil</button></td>`;
  tr.querySelector(".sil").addEventListener("click", () => tr.remove());
  $("pm-satirlar").appendChild(tr);
}
$("pm-ekle").addEventListener("click", () => partiSatiri());
let sonBirimMaliyet = null;
$("form-maliyet").addEventListener("submit", (e) => {
  e.preventDefault();
  calistir(e.submitter, "pm-hata", async () => {
    const v = await gonder("/api/maliyet-yontemi", {
      partiler: [...$("pm-satirlar").rows].map((r) => ({
        miktar: sayiOku(r.querySelector(".pm-miktar").value),
        birim_maliyet: sayiOku(r.querySelector(".pm-maliyet").value),
      })),
      satilan_miktar: sayi("satilan_miktar"),
      yontem: $("maliyet_yontemi").value,
      yerine_koyma_maliyeti: sayi("pm_yerine_koyma"),
    });
    const s = v.sonuc;
    sonBirimMaliyet = s.birim_maliyet;
    $("pm-birim").textContent = tl(s.birim_maliyet);
    $("pm-degisim").textContent = isaretli(s.stok_deger_degisimi);
    $("pm-artis").textContent = yuzde(s.fiyat_artisi_orani);
    $("pm-kalan").textContent = `${B2.format(s.kalan_miktar)} adet · ${tl(s.kalan_stok_degeri)}`;
    $("pm-durum").textContent = "";
    $("pm-sonuc").hidden = false;
  });
});
$("pm-aktar").addEventListener("click", () => {
  if (sonBirimMaliyet === null) return;
  $("ilk_alis_maliyeti").value = Number(sonBirimMaliyet.toFixed(6));
  $("yerine_koyma_maliyeti").value = $("pm_yerine_koyma").value;
  $("pm-durum").textContent = "Aktarıldı. Ürün analizi güncelleniyor.";
  sekmeAc($("t-urun"));
  onizlemeIste();
});

// ============================================================ FİNANSMAN
$("form-erken").addEventListener("submit", (e) => {
  e.preventDefault();
  calistir(e.submitter, "eo-hata", async () => {
    const v = await gonder("/api/finansman/erken-odeme", { parametreler: parametreler(), girdi: {
      fatura_tutari: sayi("fatura_tutari"), iskonto_yuzde: sayi("iskonto_yuzde"), vade_gun: sayi("vade_gun"),
    } });
    const s = v.sonuc;
    $("eo-karar").textContent = s.karar;
    $("eo-karar").className = "vurgu-metin";
    $("eo-pesin").textContent = tl(s.pesin_odeme);
    $("eo-vadeli").textContent = tl(s.vadeli_odemenin_bugunku_degeri);
    $("eo-ortuk").textContent = yuzdeBicim2.format(s.ortuk_yillik_oran);
    $("eo-efektif").textContent = yuzdeBicim2.format(s.ortuk_efektif_yillik_oran);
    $("eo-sonuc").hidden = false;
  });
});

function krediSatiri(a = {}) {
  const tr = document.createElement("tr");
  tr.innerHTML = `<td><input class="kr-ad" value="${kacis(a.ad ?? "")}" aria-label="Ad"></td>
    <td><select class="kr-tur" aria-label="Tür">
      <option value="esit_taksitli"${a.tur === "tek_odemeli" ? "" : " selected"}>Eşit taksitli</option>
      <option value="tek_odemeli"${a.tur === "tek_odemeli" ? " selected" : ""}>Tek ödemeli</option></select></td>
    <td><input class="kr-tutar" type="number" step="any" value="${kacis(a.tutar ?? "")}" aria-label="Tutar"></td>
    <td><input class="kr-faiz" type="number" step="any" value="${kacis(a.faiz ?? "")}" aria-label="Yıllık faiz"></td>
    <td><input class="kr-ay" type="number" step="1" value="${kacis(a.ay ?? "")}" aria-label="Vade ay"></td>
    <td><input class="kr-masraf" type="number" step="any" value="${kacis(a.masraf ?? 0)}" aria-label="Peşin masraf"></td>
    <td><button type="button" class="sil" aria-label="Alternatifi sil">Sil</button></td>`;
  tr.querySelector(".sil").addEventListener("click", () => tr.remove());
  $("kr-satirlar").appendChild(tr);
}
$("kr-ekle").addEventListener("click", () => krediSatiri({ ad: `Alternatif ${$("kr-satirlar").rows.length + 1}` }));

$("form-kredi").addEventListener("submit", (e) => {
  e.preventDefault();
  calistir(e.submitter, "kr-hata", async () => {
    const alternatifler = [...$("kr-satirlar").rows].map((r) => ({
      ad: r.querySelector(".kr-ad").value.trim(), tur: r.querySelector(".kr-tur").value,
      kullanilan_tutar: sayiOku(r.querySelector(".kr-tutar").value),
      yillik_faiz_yuzde: sayiOku(r.querySelector(".kr-faiz").value),
      vade_ay: sayiOku(r.querySelector(".kr-ay").value), pesin_masraf: sayiOku(r.querySelector(".kr-masraf").value) ?? 0,
    }));
    const v = await gonder("/api/finansman/karsilastir", { parametreler: parametreler(), girdi: { alternatifler } });
    const s = v.sonuc;
    $("kr-ozet").textContent = `En düşük efektif maliyet: ${s.en_dusuk_efektif_maliyet} · ` +
      `paranın maliyetine göre en ucuz: ${s.en_dusuk_bugunku_deger_maliyeti}`;
    $("kr-tablo").innerHTML = s.alternatifler.map((a) => `<tr>
      <td>${kacis(a.ad)}</td><td class="sag">${tl(a.net_kullanilan, 0)}</td><td class="sag">${tl(a.toplam_geri_odeme, 0)}</td>
      <td class="sag">${tl(a.toplam_faiz_ve_masraf, 0)}</td><td class="sag">${yuzdeBicim2.format(a.efektif_yillik_maliyet)}</td>
      <td class="sag ${renk(-a.bugunku_deger_maliyeti)}">${isaretli(a.bugunku_deger_maliyeti, 0)}</td></tr>`).join("");
    const adlar = s.alternatifler.map((a) => a.ad);
    $("kr-duyarlilik-bas").innerHTML = `<tr><th>Paranın maliyeti</th>${adlar.map((a) => `<th class="sag">${kacis(a)}</th>`).join("")}<th>En ucuz</th></tr>`;
    $("kr-duyarlilik").innerHTML = s.duyarlilik.map((d) => `<tr><td>%${B1.format(d.yillik_oran_yuzde)}</td>` +
      adlar.map((a) => `<td class="sag">${isaretli(d.bugunku_deger_maliyetleri[a], 0)}</td>`).join("") +
      `<td>${kacis(d.en_ucuz)}</td></tr>`).join("");
    varsayimYaz("kr-varsayimlar", s.varsayimlar);
    $("kr-durum").textContent = `Kaydedildi · analiz no ${v.kayit_id}`;
    $("kr-sonuc").hidden = false;
    ciz("g-finansman", v.grafik);
  });
});

// ============================================================ başlangıç
async function baglantiKontrol() {
  const rozet = $("baglanti");
  try {
    const v = await (await fetch("/api/saglik")).json();
    rozet.dataset.durum = "ok";
    rozet.textContent = "Hesap motoru bağlı";
    $("surum").textContent = "motor v" + v.motor_surumu;
  } catch {
    rozet.dataset.durum = "hata";
    rozet.textContent = "Hesap motoruna ulaşılamadı";
  }
}

varsayilanSenaryolar();
partiSatiri(100, 80);
partiSatiri(200, 100);
krediSatiri({ ad: "Banka A", tur: "esit_taksitli", tutar: 1000000, faiz: 42, ay: 12, masraf: 5000 });
krediSatiri({ ad: "Banka B", tur: "tek_odemeli", tutar: 1000000, faiz: 45, ay: 6, masraf: 0 });
cubukAraliklari();
const baslangic = sekmeler.find((s) => "#" + s.id.slice(2) === location.hash);
if (baslangic) sekmeAc(baslangic);
baglantiKontrol().then(onizlemeIste);
