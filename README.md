# Deskripsi
Aplikasi ini adalah aplikasi untuk simulasi koneksi TCP di atas UDP dengan algoritma Go-Back-N. Terdapat server dan client di aplikasi ini di mana server akan mengirimkan data ke semua client yang terhubung melalui algoritma Go-Back-N. Server dan client berkomunikasi menggunakan socket UDP yang diimplementasikan melalui library Socket dari Python. Sebelum pengiriman data, server akan melakukan Three Way Handshake dengan semua client yang terhubung.

# Cara Penggunaan
1. Jalankan server dengan perintah beserta argumen `python3 server.py {port} {path/to./data}`
2. Jalankan client dengan perintah beserta argumen `python3 client.py {port} {path/to/save/data}`
3. Pastikan port client dan server sama.
4. Anda bisa membuat lebih dari satu instansi client, untuk menerima lebih dari satu client, jawab prompt "Listen more?" dengan "y".
5. Ketika prompt "Listen more?" dijawab dengan "n", maka server akan mengirimkan file ke semua client yang terhubung.

# Simulasi Traffic
- Anda dapat menyimulasikan traffic antara server dan client dengan perintah `tc qdisc add dev lo root netem delay 100ms 50ms reorder 8% corrupt 5% duplicate 2% 5% loss 5%`
- Untuk menghilangkan traffic control tersebut, jalankan perintah `tc qdisc del dev lo root netem`