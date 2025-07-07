from flask import Flask, render_template, jsonify
import requests
import numpy as np
import copy
import random
import traceback

app = Flask(__name__)

# Data masalah menggunakan lat/lon
problem_data = {
    "depot": {"name": "Depot", "lat": -6.185875070871443, "lon": 106.779258142967, "demand": 0},
"customers": [
        {"id": 1, "name": "Pelanggan A", "lat": -6.259972903118333, "lon": 106.82681300383585, "demand": 10},
        {"id": 2, "name": "Pelanggan B", "lat": -6.262689337785392, "lon": 106.83611277989932, "demand": 10},
        {"id": 3, "name": "Pelanggan C", "lat": -6.267616787850371, "lon": 106.83329530788009, "demand": 10},
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


# "Memori" Server
BEST_SOLUTION_EVER = None
INITIAL_SOLUTION_BASELINE = None
DISTANCE_MATRIX = None

def create_distance_matrix_osrm(data):
    """Mengambil matriks JARAK (distances) dari OSRM."""
    global DISTANCE_MATRIX
    if DISTANCE_MATRIX is not None: return True
    
    locations = [data['depot']] + data['customers']
    coords_str = ";".join([f"{loc['lon']},{loc['lat']}" for loc in locations])
    url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}?annotations=distance"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        json_data = response.json()
        if json_data['code'] == 'Ok':
            DISTANCE_MATRIX = np.array(json_data['distances'])
            print("INFO: Matriks JARAK berhasil dibuat dari OSRM.")
            return True
        else: return False
    except requests.exceptions.RequestException: return False

def get_route_geometry(waypoints):
    """Hanya mengambil bentuk jalan (geometry) untuk digambar di peta."""
    coords_str = ";".join([f"{wp['lon']},{wp['lat']}" for wp in waypoints])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        json_data = response.json()
        if json_data['code'] == 'Ok' and json_data['routes']:
            route = json_data['routes'][0]
            # Tukar lon,lat dari OSRM menjadi lat,lon untuk Leaflet
            geometry = [[coord[1], coord[0]] for coord in route['geometry']['coordinates']]
            return geometry
    except requests.exceptions.RequestException: return []
    return []

def process_solution_details(solution_routes, data):
    """Menghitung detail dan mengambil geometri untuk setiap rute."""
    route_details = []
    total_distance_meters = 0
    customer_map = {c['id']: c for c in data['customers']}
    id_to_matrix_index = {c['id']: i + 1 for i, c in enumerate(data['customers'])}

    for i, route_ids in enumerate(solution_routes):
        if not route_ids: continue
        
        route_distance, route_load = 0, 0
        last_idx = 0
        for cust_id in route_ids:
            current_idx = id_to_matrix_index[cust_id]
            route_distance += DISTANCE_MATRIX[last_idx][current_idx]
            route_load += customer_map[cust_id]['demand']
            last_idx = current_idx
        route_distance += DISTANCE_MATRIX[last_idx][0]
        total_distance_meters += route_distance
        
        waypoints_for_route = [data['depot']] + [customer_map[cid] for cid in route_ids] + [data['depot']]
        geometry = get_route_geometry(waypoints_for_route)

        route_details.append({
            "vehicle_id": i + 1,
            "route_str": " -> ".join([customer_map[cid]['name'] for cid in route_ids]),
            "distance_km": route_distance / 1000,
            "load": route_load,
            "geometry": geometry,
        })
        
    return {"total_distance_km": total_distance_meters / 1000, "route_details": route_details}

def get_a_solution(data):
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
    if not create_distance_matrix_osrm(problem_data):
        return "Gagal menginisialisasi data dari server pemetaan."
    return render_template('index.html', data=problem_data)

@app.route('/solve', methods=['POST'])
def solve():
    try:
        global BEST_SOLUTION_EVER, INITIAL_SOLUTION_BASELINE
        if DISTANCE_MATRIX is None:
            return jsonify({"error": "Matriks jarak belum dibuat."}), 500

        if INITIAL_SOLUTION_BASELINE is None:
            INITIAL_SOLUTION_BASELINE = process_solution_details(get_a_solution(problem_data), problem_data)
            BEST_SOLUTION_EVER = INITIAL_SOLUTION_BASELINE

        num_simulations = 20
        best_in_this_run = None
        for _ in range(num_simulations):
            candidate_details = process_solution_details(get_a_solution(problem_data), problem_data)
            if best_in_this_run is None or candidate_details['total_distance_km'] < best_in_this_run['total_distance_km']:
                best_in_this_run = candidate_details

        if best_in_this_run['total_distance_km'] < BEST_SOLUTION_EVER['total_distance_km']:
            BEST_SOLUTION_EVER = best_in_this_run
            print(f"INFO: REKOR BARU DITEMUKAN! Jarak: {BEST_SOLUTION_EVER['total_distance_km']:.2f} km")
                
        return jsonify({
            "initial": INITIAL_SOLUTION_BASELINE,
            "best_option": BEST_SOLUTION_EVER,
            "current_trial": best_in_this_run
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Terjadi error internal di server: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)