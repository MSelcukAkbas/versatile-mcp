# Versatile-Remote 🛰️

Versatile-Remote, MCP (Model Context Protocol) ekosistemi için tasarlanmış, **Yüksek Performanslı ve Asenkron bir SSH Sunucusudur.** 

Bu sunucu, WSL veya harici binary bağımlılıkları olmadan, saf Python (`asyncssh`) motoruyla uzak sunucularda komut koşturmak için optimize edilmiştir.

## 🚀 Öne Çıkan Özellikler

- **Native AsyncSSH:** Harici kabuk katmanı olmadan doğrudan bağlantı.
- **Connection Caching:** Aynı host/user ikilisi için bağlantıyı açık tutarak milisaniyeler seviyesinde ardışık komut çalıştırma.
- **Kusursuz JSON Yanıtları:** Exit code, stdout ve stderr bilgilerini yapılandırılmış şekilde döner.
- **Zero-Dependency (External):** Sadece Python kütüphanelerine güvenir, işletim sisteminden `sshpass` gibi araçlar beklemez.

## 🛠️ Araçlar

### `ssh_execute`
Uzak sunucuda güvenli ve hızlı bir komut çalıştırır.

**Parametreler:**
- `host`: Hedef IP veya Hostname.
- `user`: SSH kullanıcı adı.
- `password`: SSH şifresi.
- `command`: Çalıştırılacak komut.
- `timeout`: Zaman aşımı süresi (Varsayılan: 30s).

## ⚙️ Kurulum

### 1. Hazırlık
Dizine gidin ve bağımlılıkları kurun:
```bash
pip install -r requirements.txt
```

### 2. Ortam Değişkenleri
Bir `.env` dosyası oluşturarak ayarlarınızı yapabilirsiniz (Opsiyonel).

### 3. Claude Desktop Entegrasyonu
`claude_desktop_config.json` dosyanıza şu bloğu ekleyin:

```json
"versatile-remote": {
  "command": "python",
  "args": ["c:/Users/akbas/Desktop/Mcp/versatile-remote/main.py"],
  "env": {}
}
```

## 🏗️ Mimari
Bu sunucu, her bir fonksiyonun kendi başına bir mikro-sunucu olduğu **Micro-Modular Architecture**'ın bir parçasıdır. Geri kalan araçlar için **mcp_master** veya **Versatile-Brain** sunucularını kullanabilirsiniz.

---
**Versatile-MCP Suite**'in bir parçasıdır.
