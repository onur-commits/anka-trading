# CLAUDE.md — Anka Trading Çalışma Kuralları

## Ana Prensip

Görevi sonuna kadar otonom tamamla. Mevcut sistemi koru. Yan görevlere sapma. Zorunlu durumlar dışında kullanıcıyı bölme.

## Çalışma Modu

Görev netse uygula. Gereksiz soru sorma. Sonuca ulaşana kadar çalış. Kullanıcı bilgisayar başında olmayabilir. Makul teknik kararları bağımsız al. Belirsizlik nedeniyle işi durdurma. En mantıklı çözümü uygula ve raporla.

## Yetkiler

Kod yazabilirsin. Dosya oluşturabilirsin. Dosya düzenleyebilirsin. Hata düzeltebilirsin. Eksik parçaları tamamlayabilirsin. Test çalıştırabilirsin. Build ve compile işlemleri yapabilirsin. Commit oluşturabilirsin.

## Yasaklar

Git pull yapma.
Git push yapma.
Branch değiştirme.
Force push yapma.
Eski session görevlerini geri getirme.
Canlı trade tetikleme.
Çalışan sistemi bozacak yıkıcı komutlar kullanma.
Gereksiz dosya silme.
Ana görev dışına çıkma.

## Git Kuralları

Mevcut branch üzerinde çalış.
Remote’dan kod çekme.
Remote’a kod gönderme.
Branch değiştirme.
Sadece gerekli dosyaları değiştir.
Commit gerekiyorsa kısa ve net mesajla commit oluştur.
Commit mesajına Claude generated gibi ifadeler ekleme.

## Canlı Sistem Güvenliği

Bu proje gerçek para ve canlı trading sistemiyle ilişkili olabilir.
Canlı alım satım tetikleme.
Emir gönderme.
Otomatik trader çalıştırma.
API ile emir verme.
Botu canlı moda alma.
Riskli script çalıştırma.

Sadece dry-run, paper, tara, analiz veya durum kontrolü güvenlidir.

## Çalışan Sistemi Koruma

Mevcut çalışan yapıyı bozma.
Eski çalışan fonksiyonları kaldırma.
Gereksiz refactor yapma.
UI/startup akışını bozma.
Coin modüllerini ana akışa dahil etme.
BIST odağını koru.

## Kodlama Kuralları

Eksik parçaları tamamla.
Aynı hatayı tekrar etme.
Önce mevcut yapıyı anla.
Sonra minimum ve doğru müdahale yap.
Hata varsa sebebini bulup kökten düzelt.
Parça parça çözüm verme.
Final kod çalışır durumda olsun.

## Test Kuralları

Mümkünse syntax check yap.
Mümkünse import testi yap.
Mümkünse uygulama başlatma testi yap.
Test sonucu raporla.
Test edemediysen nedenini açıkça yaz.

## Kullanıcıyı Bölme Kuralları

Gereksiz soru sorma.
Belirsizlik varsa en mantıklı varsayımı seç.
Sadece geri alınamaz, yıkıcı veya para/trade etkili işlemde dur.
Aksi halde devam et.

## Raporlama Formatı

İş bitince kısa rapor ver:

1. Ne yapıldı
2. Hangi dosyalar değişti
3. Test sonucu
4. Etki analizi
5. Risk var mı yok mu

## Bu Oturum İçin Ek Kurallar

Remote Control aktifse işleri otonom yürüt.
Worktree izolasyonunu koru.
Eski session görevlerini otomatik geri getirme.
Ana repo ve çalışan sistem korunacak.
Git pull/push yok.
Canlı trade yok.
İş bitince net sonuç raporu ver.
