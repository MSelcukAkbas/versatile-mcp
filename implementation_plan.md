# Bütünleşik Zeka: Versatile-Memory'yi Versatile-Mcp'ye Entegre Etme Planı

Bu plan, `Versatile-Mcp` içerisindeki zayıf/eski hafıza araçlarını (`commit_knowledge`, `search_knowledge`, `list_knowledge`, `manage_knowledge`) tamamen kaldırıp, yerine `Versatile-Memory`'nin gelişmiş (ChromaDB + SQLite, Graph, Traceable Reasoning) yapısını tek bir sunucuda birleştirmeyi hedefler.

## User Review Required

> [!WARNING]
> **Kritik Değişiklik:** Bu geçiş (migration) yapıldığında, ajanların hafıza yönetimi tamamen değişecektir. Önceden sadece metin (string) olarak saklanan veriler, artık `project_root` ve `namespace` bazlı sıkı bir vektörel/graf (Graph) yapısında tutulacaktır. 

> [!IMPORTANT]
> **Asenkron/Senkron Uyumu:** Versatile-Memory senkron çalışırken, Versatile-Mcp asenkron çalışmaktadır. FastMCP senkron fonksiyonları otomatik olarak "Thread Pool" (arka plan iş parçacığı) içinde asenkron bozmadan çalıştırabildiği için, veritabanı kodlarını baştan yazmak yerine doğrudan entegre edeceğiz.

## Open Questions

> [!CAUTION]
> Lütfen uygulamaya geçmeden önce şu soruları yanıtla:
> 1. **Reasoning (Akıl Yürütme) Değişimi:** Eski bellek araçlarını kaldırırken, Versatile-Mcp içindeki eski `sequentialthinking` aracını da kaldırıp yerine Versatile-Memory'nin `sequentialthinking_add_thought` (Graph ve Trace destekli) aracını koyalım mı? (Önerilen: **Evet**, sistem bütünlüğü için.)
> 2. **Klasör Yapısı:** Versatile-Memory'yi `Versatile-Mcp/servers/brain/` içine mi gömeyim (eski brain'i silerek), yoksa `Versatile-Mcp/servers/memory/` adında yepyeni bir katman olarak mı ekleyeyim? (Önerilen: **Brain katmanını tamamen Versatile-Memory ile değiştirmek**).

---

## Proposed Changes

Aşağıda yapılacak değişikliklerin adım adım dökümü bulunmaktadır.

### 1. Eski Brain Katmanının Temizlenmesi
Versatile-Mcp içindeki zayıf hafıza ve akıl yürütme servisleri kaldırılacak.

#### [DELETE] `servers/brain/services/memory/`
#### [DELETE] `servers/brain/services/reasoning/`
#### [DELETE] `servers/brain/tools/memory.py`
#### [DELETE] `servers/brain/tools/reasoning.py`

### 2. Versatile-Memory'nin Taşınması (Yeni Brain Katmanı)
Versatile-Memory içindeki sağlam mimari, `Versatile-Mcp/servers/brain/` dizinine taşınacak.

#### [NEW] `servers/brain/storage/` (HybridStore, Chroma, SQLite)
#### [NEW] `servers/brain/services/` (MemoryService, ReasoningService, GraphService, RetrievalPipeline)
#### [NEW] `servers/brain/tools/` (memory_tools.py, reasoning_tools.py, graph_tools.py)
#### [NEW] `core/helpers/chunker.py` ve `embedder.py` (Versatile-Memory'den çekirdek yardımcılar eklenecek)

### 3. main.py Entegrasyonu
`Versatile-Mcp/main.py` dosyası güncellenerek, FastMCP'ye Versatile-Memory araçları yüklenecek.

#### [MODIFY] `main.py`
- `commit_knowledge` vb. araçların `register` fonksiyonları silinecek.
- Yerine `HybridStore` başlatılacak ve Versatile-Memory'deki 18 gelişmiş tool (veya seçili olanlar) eklenecek.
- Llama Engine, `HybridStore`'a referans olarak verilecek.

### 4. Bağımlılıkların Birleştirilmesi
İki projenin bağımlılıkları çakışmadan tek bir `requirements.txt` dosyasında birleştirilecek.

#### [MODIFY] `requirements.txt`
- `chromadb`
- Diğer gerekli paketler eklenecek.

---

## Verification Plan

1. **Bağımlılık Kontrolü:** `pip install -r requirements.txt` komutunun hatasız çalışması.
2. **Başlangıç (Boot) Kontrolü:** `python main.py` komutu çalıştırılarak FastMCP'nin `memory.write`, `memory.query`, `sequentialthinking_add_thought`, `ssh_execute` araçlarını tek bir sunucuda hatasız listelediği teyit edilecek.
3. **Kalıcılık Kontrolü:** `memory.write` aracı ile bir deneme verisi yazılıp, uygulamanın yeniden başlatılması sonrasında verinin ChromaDB ve SQLite'da kaldığı doğrulanacak.
