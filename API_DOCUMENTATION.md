# Dokumentasi API Sistem Integrasi Antar Layanan

## Overview
Sistem ini terdiri dari tiga layanan utama yang berkomunikasi satu sama lain menggunakan REST API:
- UserService (Port 5001)
- ProductService (Port 5002)
- OrderService (Port 5003)

## UserService API

### Provider Endpoints

#### GET /api/users
Mengambil daftar semua user.

Response:
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  }
]
```

#### GET /api/users/{id}
Mengambil detail user berdasarkan ID.

Response:
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com"
}
```

#### POST /api/users
Membuat user baru.

Request:
```json
{
  "name": "John Doe",
  "email": "john@example.com"
}
```

### Consumer Endpoints

#### GET /api/users/{id}/transactions
Mengambil riwayat transaksi user dari OrderService.

## ProductService API

### Provider Endpoints

#### GET /api/products
Mengambil daftar semua produk.

Response:
```json
[
  {
    "id": 1,
    "name": "Laptop",
    "price": 1000,
    "stock": 10
  }
]
```

#### GET /api/products/{id}
Mengambil detail produk berdasarkan ID.

Response:
```json
{
  "id": 1,
  "name": "Laptop",
  "price": 1000,
  "stock": 10
}
```

#### POST /api/products
Membuat produk baru.

Request:
```json
{
  "name": "Laptop",
  "price": 1000,
  "stock": 10
}
```

### Consumer Endpoints

#### GET /api/products/{id}/user
Mengambil informasi user terkait produk dari UserService.

## OrderService API

### Provider & Consumer Endpoints

#### POST /api/orders
Membuat order baru (mengonsumsi data dari UserService dan ProductService).

Request:
```json
{
  "user_id": 1,
  "product_id": 1,
  "quantity": 2
}
```

Response:
```json
{
  "id": 1,
  "user_id": 1,
  "product_id": 1,
  "quantity": 2,
  "total_price": 2000,
  "status": "pending"
}
```

#### GET /api/orders/{id}
Mengambil detail order dengan data lengkap dari UserService dan ProductService.

Response:
```json
{
  "id": 1,
  "user_id": 1,
  "product_id": 1,
  "quantity": 2,
  "total_price": 2000,
  "status": "pending",
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  },
  "product": {
    "id": 1,
    "name": "Laptop",
    "price": 1000,
    "stock": 10
  }
}
```

#### GET /api/orders
Mengambil daftar semua order.

## Komunikasi Antar Layanan
- OrderService bertindak sebagai consumer untuk UserService dan ProductService
- UserService bertindak sebagai provider untuk OrderService
- ProductService bertindak sebagai provider untuk OrderService 