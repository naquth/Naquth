# Setup Snake Animation

1. Upload isi folder ini ke repo profil `naquth/naquth` (branch `main`).
2. Buka tab **Actions** > **Generate Snake** > **Run workflow**.
3. Tunggu selesai, branch `output` akan berisi `snake.svg` dan `snake-dark.svg`.
4. Refresh profil GitHub kamu.

Jika nama repo/username berbeda, ganti `naquth` di `snake.yml` dan URL di `README.md`.

## Wajib: token agar kontribusi private terbaca
1. GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic) > Generate new token.
2. Centang scope `read:user`, lalu generate dan salin token.
3. Di repo profil: Settings > Secrets and variables > Actions > New repository secret.
   Name: `SNAKE_TOKEN`, Value: token tadi.
4. Jalankan ulang workflow Generate Snake.
