# Newsletter Posts

Taruh file `.md` di folder ini untuk broadcast otomatis via GitHub Actions.

## Format File

Buat file baru: `newsletter/posts/YYYY-MM-DD-judul-artikel.md`

## Frontmatter (opsional)

```markdown
---
subject: Judul email yang akan dikirim ke subscriber
date: 2026-05-20
---

Isi artikel di sini dalam format Markdown.

## Heading

Paragraf, **bold**, *italic*, [link](https://...) semua didukung.
```

## Cara Pakai

1. Buat file `.md` baru di folder ini
2. Commit & push ke branch `main`
3. GitHub Actions otomatis:
   - Konversi Markdown → HTML email
   - Kirim ke semua subscriber via MailerLite
   - Cek jumlah subscriber — kirim notif ke kamu jika sudah >= 900

> **Catatan:** Workflow hanya trigger jika ada file `.md` baru/berubah di folder `newsletter/posts/`.
