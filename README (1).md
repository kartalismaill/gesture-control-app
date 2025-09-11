# 🎮 El Hareketi ile Bilgisayar Kontrol Uygulaması

Bu proje, **MediaPipe** kütüphanesi ile el hareketlerini algılayarak bilgisayarı kontrol etmeyi sağlar.  
Kullanıcı, farklı el hareketlerini fare hareketleri, klavye kısayolları veya uygulama açma komutlarına atayabilir.  

## 🚀 Özellikler
- 🖱️ Fare kontrolü (hareket ettirme, sol/sağ tık, kaydırma)  
- ⌨️ Klavye kısayolları (ör. `ctrl+c`, `ctrl+v`, `alt+tab`)  
- 📂 Uygulama açma (örn. Not Defteri, Hesap Makinesi)  
- 📷 Canlı kamera ile el takibi  
- 🎨 Tkinter arayüzü ile hareket ekleme/silme  
- 💾 JSON dosyası ile kayıtlı komutlar  

## 📦 Gereksinimler
- Python 3.8+  
- OpenCV  
- MediaPipe  
- PyAutoGUI  
- Tkinter (Python ile birlikte gelir)  
- Pillow  

Kurulum:  
```bash
pip install opencv-python mediapipe pyautogui pillow
```

## ▶️ Kullanım
1. Repoyu klonla:
   ```bash
   git clone https://github.com/kadirkartal/gesture-control-app.git
   cd gesture-control-app
   ```
2. Python dosyasını çalıştır:
   ```bash
   python main.py
   ```
3. Kamera açıldığında el hareketlerinizi kullanarak bilgisayarı kontrol edebilirsiniz.  

## 🛠️ Dosya Yapısı
```
gesture-control-app/
│
├── main.py             # Ana uygulama
├── commands.json       # Kayıtlı hareket–komut eşleşmeleri
├── handimages/         # El hareketi görselleri
└── README.md           # Proje açıklaması
```

## 👨‍💻 Geliştirici
Bu proje, **Simurg Bilişim** staj programı kapsamında  
**Kadir Kartal** tarafından geliştirilmiştir.  
