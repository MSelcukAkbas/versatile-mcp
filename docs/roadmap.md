# Master MCP Server - Kişisel Gelişim Yol Haritası

Bu döküman, projenin senin kişisel ihtiyaçlarına göre nasıl şekilleneceğini özetler.

## 📅 Mevcut Durum (Faz 1 & Zekâ Katmanı Tamamlandı ✅)
- Ollama asenkron entegrasyonu.
- Güvenli dosya sistemi ve merkezi loglama.
- **Zekâ Katmanı**: Planlayıcı, Optimizer, Critic, Syntax Guardian ve Sequential Thinking araçları aktif.
- **Tool Envanteri**: Araçların işlev ve maliyetlerini raporlayan katalog sistemi.

---

## 🚀 Faz 2: Gelişmiş Bilgi ve Hafıza (The "Brain") - Devam Ediyor

### 1. Web Arama (Tamamlandı ✅)
- `ddgs` entegrasyonu ile asenkron bilgi çekme.

### 2. Kapsamlı Hafıza Dalları (Sıradaki 🏗️)
Hafıza sistemini şu üç kolda detaylandırıyoruz:

**A. Semantik Proje Hafızası (RAG)**
- **Amacı**: Klasöründeki binlerce satır kodu veya dökümanı asistanın "bilmesini" sağlamak.
- **Teknoloji**: `ollama.embed` + `ChromaDB` (yerel).

**B. Kişisel Olgu Hafızası (Long-term Facts)**
- **Amacı**: Senin "şunu unutma" dediğin veya öğrendiği kalıcı bilgileri saklamak.
- **Teknoloji**: SQLite tabanlı basit bir Key-Value Store.

**C. Etkileşim Geçmişi (Episodic Memory)**
- **Amacı**: O günkü koddaki değişiklikleri veya araç sonuçlarını hatırlamak.
- **Teknoloji**: JSON tabanlı kısa süreli işlem logları.

---

## 📊 Faz 3: Yönetim ve Gözlem (The "Control" Expansion)

### 3. Kullanıcı Arayüzü (Local Dashboard)
- Yerel bir web arayüzü ile logları izleme, şablonları düzenleme ve sunucu durumunu görme.

### 4. Gelişmiş Prompt Mühendisliği
- Farklı modeller için özelleşmiş yönerge setleri.
