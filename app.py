from flask import Flask, render_template, jsonify
import numpy as np
import copy
import random

# Inisialisasi Aplikasi Flask
app = Flask(__name__)

# --- Data Masalah (Studi Kasus) ---
problem_data = {
    "depot": {"lat": -6.185875070871443, "lon":  106.779258142967, "demand": 0},
    "customers": [
        {"id": 1, "name": "Pelanggan A", "lat": -6.181501841975548, "lon": 106.77949954175816, "demand": 10},
        {"id": 2, "name": "Pelanggan B", "lat": -6.1745079117196715, "lon": 106.78572935282715, "demand": 10},
        {"id": 3, "name": "Pelanggan C", "lat": -6.161537171070607, "lon": 106.76504415822328, "demand": 10},
        {"id": 4, "name": "Pelanggan D", "lat": -6.178433204859067, "lon": 106.76864904697906, "demand": 10},
        {"id": 5, "name": "Pelanggan E", "lat": -6.192541460600721, "lon": 106.77280470224031, "demand": 10},
        {"id": 6, "name": "Pelanggan F", "lat": -6.182984429170896, "lon": 106.7523769992909, "demand": 10},
        {"id": 7, "name": "Pelanggan G", "lat": -6.197661227734034, "lon": 106.77400633182557, "demand": 10},
        {"id": 8, "name": "Pelanggan H", "lat": -6.159261766086418, "lon": 106.76662489294469, "demand": 10},
        {"id": 9, "name": "Pelanggan I", "lat": -6.162760498959078, "lon": 106.76593824803936, "demand": 10},
    ],
    "vehicle_capacity": 30,
    "num_vehicles": 3
}

# --- Logika Algoritma ---

def get_customer_by_id(customer_id, customers):
    """Mencari data pelanggan berdasarkan ID."""
    for customer in customers:
        if customer['id'] == customer_id:
            return customer
    return None

def calculate_distance(c1, c2):
    """Menghitung jarak Haversine antara dua koordinat."""
    R = 6371  # Radius bumi dalam km
    lat1, lon1 = np.radians(c1['lat']), np.radians(c1['lon'])
    lat2, lon2 = np.radians(c2['lat']), np.radians(c2['lon'])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def process_solution_details(solution_routes, customers, depot):
    """
    FUNGSI BARU: Memproses rute untuk mendapatkan detail lengkap
    termasuk jarak per rute, beban, dan format string.
    """
    route_details = []
    total_distance = 0
    
    # Buat dictionary untuk mapping ID ke Nama Pelanggan
    customer_map = {c['id']: c for c in customers}

    for i, route_ids in enumerate(solution_routes):
        if not route_ids:
            continue
        
        route_distance = 0
        route_load = 0
        
        # Jarak dari depot ke pelanggan pertama
        first_customer = customer_map[route_ids[0]]
        route_distance += calculate_distance(depot, first_customer)
        
        # Jarak antar pelanggan
        for j in range(len(route_ids) - 1):
            cust1 = customer_map[route_ids[j]]
            cust2 = customer_map[route_ids[j+1]]
            route_distance += calculate_distance(cust1, cust2)
            route_load += cust1['demand']
            
        # Tambahkan demand pelanggan terakhir
        last_customer = customer_map[route_ids[-1]]
        route_load += last_customer['demand']

        # Jarak dari pelanggan terakhir ke depot
        route_distance += calculate_distance(last_customer, depot)
        
        total_distance += route_distance
        
        # Format string rute
        route_str = " -> ".join([customer_map[cid]['name'] for cid in route_ids])

        route_details.append({
            "vehicle_id": i + 1,
            "route_str": route_str,
            "distance": route_distance,
            "load": route_load,
            "customer_ids": route_ids # Simpan ID asli untuk menggambar di peta
        })
        
    return {"total_distance": total_distance, "route_details": route_details}


def get_initial_solution(data):
    """Membuat solusi awal dengan pendekatan greedy."""
    customers = list(data['customers'])
    random.shuffle(customers)
    routes = [[] for _ in range(data['num_vehicles'])]
    loads = [0] * data['num_vehicles']
    
    for customer in customers:
        for i in range(data['num_vehicles']):
            if loads[i] + customer['demand'] <= data['vehicle_capacity']:
                routes[i].append(customer['id'])
                loads[i] += customer['demand']
                break
    
    return routes

@app.route('/')
def index():
    """Menampilkan halaman utama."""
    return render_template('index.html', data=problem_data)

@app.route('/solve', methods=['POST'])
def solve():
    """API endpoint untuk menjalankan optimisasi."""
    initial_routes = get_initial_solution(problem_data)
    initial_solution_details = process_solution_details(initial_routes, problem_data['customers'], problem_data['depot'])
    
    # Simulasi optimisasi
    optimized_data = copy.deepcopy(problem_data)
    optimized_data['customers'].sort(key=lambda c: c['lat'])
    optimized_routes = get_initial_solution(optimized_data)
    optimized_solution_details = process_solution_details(optimized_routes, optimized_data['customers'], problem_data['depot'])

    return jsonify({
        "initial": initial_solution_details,
        "optimized": optimized_solution_details
    })

if __name__ == '__main__':
    app.run(debug=True)