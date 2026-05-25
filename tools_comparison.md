# MCP Araçları (Tools) Karşılaştırması

Bu belge, **Versatile-Memory** (v2) ve **Versatile-Mcp** sunucularının ajana sunduğu tüm araçların (tools) listelerini ve birbirleriyle örtüşen/benzer araçların karşılaştırmasını içerir.

---

## 1. Versatile-Memory Araç Listesi (18 Araç)

Bu sunucu tamamen **Kalıcı Hafıza, İzlenebilir Akıl Yürütme ve İlişkisel Graph** üzerine uzmanlaşmıştır. (v2 isimlendirme standartlarını kullanır)

### Hafıza (Memory)
1. `memory.write`: Ana hafızaya yeni bir bilgi (append-only) yazar ve versiyon zinciri başlatır.
2. `memory.update`: Mevcut bir bilginin üzerine yazar (eskiyi superseded yapar).
3. `memory.get`: ID'si verilen spesifik bir hafıza kaydını getirir.
4. `memory.query`: Vektörel arama, Graph genişletmesi ve metadata filtrelemesi ile semantik arama yapar.
5. `memory.index`: Dokümanları veya kod tabanını parçalayarak (chunking) vektör veritabanına indeksler.

### Akıl Yürütme (Reasoning)
6. `sequentialthinking_add_thought`: Ajanın kompleks düşünce adımlarını işler. Loop ve çelişki kontrolü yapar.
7. `reasoning_trace_write`: Manuel olarak bir varsayım veya çıkarım (inference) kaydeder.
8. `reasoning_trace_query`: Sadece ajanın eski düşünce izleri (traces) arasında arama yapar.
9. `reasoning_distill`: Kesinleşen düşünce sonuçlarını (%85+ güvenilirlikle) kalıcı ana hafızaya aktarır.

### Graph (İlişki)
10. `graph.expand`: Bir hafıza düğümünden başlayarak ilişkili diğer kayıtları (bağımlılıkları) getirir.
11. `graph.get_neighbors`: Doğrudan bağlı olan 1. derece komşu kayıtları getirir.
12. `graph.link`: İki hafıza veya düşünce kaydı arasına manuel bağ (`derives_from`, vb.) ekler.

### Kod Tabanı (Codebase)
13. `codebase.scan`: Projeyi dıştan içe tarayıp analiz eder (v2'de pending/hazırlık aşamasında).
14. `codebase.update_index`: Değişen kod dosyalarının vektörel indeksini günceller.

### Kapsamlı Hafıza (Scoped Memory)
15. `user.memory.get` / 16. `user.memory.set`: Kullanıcıya (User) özel tercihleri okur/yazar.
17. `project.memory.get` / 18. `project.memory.set`: Sadece spesifik projeye ait hafızayı okur/yazar.

---

## 2. Versatile-Mcp Araç Listesi (14 Araç)

Bu sunucu bir **"Ajan İşletim Sistemi (Agentic OS)"** gibi davranarak dosya, uzak sunucu ve temel hafıza yeteneklerini birleştirir.

### Uzak Sunucu (Remote / SSH)
1. `ssh_execute`: Uzak sunucuya asenkron veya senkron SSH üzerinden komut gönderir.
2. `check_job_status`: Arka planda (async) çalışan SSH işlerinin durumunu (başarılı/hata) ve çıktılarını döner.
3. `get_ssh_history`: Geçmiş SSH bağlantılarının ve çalıştırılan komutların denetim (audit) logunu getirir.

### Sistem ve Dosya (Master)
4. `validate_syntax`: Python, JS, TS, JSON vb. dosyaların sözdizimini (syntax) çalıştırılmadan önce kontrol eder.
5. `read_rich_document`: PDF, Word, EPUB gibi zengin formatlı veya normal metin dosyalarını hatasız okur.
6. `directory_tree`: Klasör ağacını çıkarır (Gizli dosyaları ve gitignore'u dikkate alır).
7. `grep_search`: Klasör içinde "ripgrep" kullanarak inanılmaz hızlı, tam eşleşmeli metin araması yapar.
8. `system_info`: İşletim sistemi, RAM, CPU ve disk kullanım istatistiklerini getirir.

### Zeka ve Hafıza (Brain)
9. `workspace_summary`: Proje kök dizinini analiz edip dillerin dağılımını ve çalışma alanı istatistiklerini çıkarır.
10. `sequentialthinking`: Ajanın adım adım mantık yürütmesini ve kendi döngülerinden kaçınmasını sağlar.
11. `commit_knowledge`: Önemli bir kuralı veya bilgiyi kalıcı hafızaya yazar.
12. `search_knowledge`: Kaydedilmiş hafızada semantik (vektörel) soru/cevap araması yapar.
13. `list_knowledge`: Tüm hafıza kayıtlarını kategorilerine göre listeler.
14. `manage_knowledge`: Yanlış olan eski hafıza kayıtlarını günceller (update) veya siler (delete).

---

## 3. Benzer ve Örtüşen Araçlar (Karşılaştırma)

Bu iki sunucu birleştirilecekse (veya paralel kullanılacaksa) aşağıdaki araçlar temelde **aynı amaca** hizmet etmektedir.

| Amaç | Versatile-Memory (Gelişmiş) | Versatile-Mcp (Pratik) | Fark / Açıklama |
| :--- | :--- | :--- | :--- |
| **Düşünce Süreci (Reasoning)** | `sequentialthinking_add_thought`<br>`reasoning_distill`<br>`reasoning_trace_*` | `sequentialthinking` | **Versatile-Memory** her düşünceyi veritabanına iz olarak bırakır ve manuel `distill` (damıtma) ister. **Versatile-Mcp** ise sadece RAM'de tutar, süreç bitince otomatik kaydeder. |
| **Hafıza Ekleme/Güncelleme** | `memory.write`<br>`memory.update` | `commit_knowledge`<br>`manage_knowledge` | **Versatile-Memory**, silme işlemini desteklemez (Append-Only/Superseded). ChromaDB kullanır. **Versatile-Mcp**, doğrudan silmeye (`delete`) izin verir ve arka planda Numpy/SQLite kullanır. |
| **Hafıza Arama** | `memory.query`<br>`memory.get` | `search_knowledge`<br>`list_knowledge` | **Versatile-Memory**, bir hafıza kaydını bulduğunda `graph.expand` ile onunla ilişkili (komşu) diğer bilgileri de zincirleme getirebilir. **Versatile-Mcp** sadece o bilginin kendisini döner. |
| **Proje/Kod İnceleme** | `codebase.scan` *(Pending)* | `directory_tree`<br>`workspace_summary` | **Versatile-Memory**'de bu araç kodun "anlamını" vektörlere dönüştürmeyi hedefler. **Versatile-Mcp** ise mevcut haliyle fiziksel dosya yapısını ve uzantı istatistiklerini mükemmel şekilde çıkarır. Birleşme durumunda harika bir sinerji noktasıdır. |
| **Dosya Okuma (Ingestion)** | `memory.index` | `read_rich_document` | **Versatile-Memory** dosyayı okuyup anında chunk'lara böler ve vektör DB'ye atar. **Versatile-Mcp** ise dokümanı ajanın anlık okuması için (str) döndürür. |
