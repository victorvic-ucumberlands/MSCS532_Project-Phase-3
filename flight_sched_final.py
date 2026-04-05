#Flight Booking & Route Optimization System
#Proof of concept implementation for data structures and core logic of the flight scheduling system.
"""
Implements the three data structures defined in Phase 1:
  1. AirportRegistry  — Hash table for O(1) airport lookup
  2. FlightGraph      — Weighted directed graph (adjacency list)
  3. MinHeap          — Binary min-heap priority queue
 
Each class is self-contained and independently testable.
"""

import re
 
import heapq
from typing import Optional
 
# ══════════════════════════════════════════════════════════════
# Airport Registry  —  Hash Table for quick airport metadata lookup
#Implemented using python's built-in dict for O(1) average-case complexity on insertions and lookups.
#Easy and simple, since we don't need to implement a heap based on the hash table

 
class AirportRegistry:
    """
    Hash table that maps IATA airport codes to airport metadata.
 
    Keys   : IATA code (str), e.g. "00SC"
    Values : list of metadata fields (name, city, country)  

    """
 
    def __init__(self):
        self._table: dict[str, tuple[str, str, str]] = {}
 
    #Add new airport or update existing one
 
    def add_airport(self, code: str, name: str, city: str, country: str) -> None:
        """Register an airport
        If the code already exists, it will be overwritten with the new metadata.
        Make sure to use uppercase IATA codes for consistency.
        """
        self._table[code.upper()] = (name, city, country)

    #Remove airport by code
 
    def remove_airport(self, code: str) -> bool:
        """Remove an airport by code. Returns True if it existed."""
        return self._table.pop(code.upper(), None) is not None
 
    #Lookup by code
    #Might return the metadata tuple (name, city, country) or None if the code is not found
 
    def get_airport(self, code: str) -> Optional[dict]:
        """ookup by IATA code. Returns None if not found."""
        return self._table.get(code.upper())
    
    #Reverse lookup by name
    #Expect to be used only during initial user query parsing 
    #Match for regex and may return multiple matches. Will ask user to disambiguate if multiple matches
    #Return code, name, city, country for each match
    def get_codes_by_name(self, query: str) -> list[tuple[str, str, str, str]]:
        """
        Reverse lookup: regex query → list of matching IATA codes from airport name 
        """
        matches = []
        pattern = re.escape(query)
        for code, info in self._table.items():
            name = info[0]
            if re.search(pattern, name, re.IGNORECASE):
                matches.append((code, info[0], info[1], info[2]))
        return matches

    
    #Reverse lookup by city 
    #Return code, name, city, country for each match
    def get_codes_by_city(self, city: str) -> list[tuple[str, str, str, str]]:
        """
        Reverse lookup: city name → list of matching IATA codes from city name 
        """
        matches = []
        pattern = re.escape(city)
        for code, info in self._table.items():
            city_name = info[1]
            if re.search(pattern, city_name, re.IGNORECASE):
                matches.append((code, info[0], info[1], info[2]))
        return matches
    
    def exists(self, code: str) -> bool:
        """existence check."""
        return code.upper() in self._table
 
    def all_codes(self) -> list[str]:
        """Return all registered IATA codes."""
        return list(self._table.keys())
 
    def all_airports(self) -> list[tuple[str, tuple[str, str, str] ]]:
        """Return list of (code, metadata) pairs."""
        return list(self._table.items())

""" 
    # ── Helpers ───────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._table)
 
    def __repr__(self) -> str:
        return f"AirportRegistry({len(self)} airports)"

""" 

 
# ══════════════════════════════════════════════════════════════
#flight grap: constrtuct the graph based on nodes with a list of edges, and each edge having the target, travel time, cost and flight id

class FlightEdge:
    """
    Represents a destination airport 
  
    destination  : IATA code of the arrival airport
    travel_time  : flight duration in minutes
    cost         : one-way ticket price in USD
    flight_id    : unique flight identifier 
    """
 
    __slots__ = ("destination", "travel_time", "cost", "flight_id")

    #Create node on initialization, no overloads 
 
    def __init__(self, destination: str, travel_time: int,
                 cost: float, flight_id: str):
        self.destination = destination
        self.travel_time = travel_time   # minutes
        self.cost        = cost          # USD
        self.flight_id   = flight_id

    #Return weight based on optimization mode 
 
    def weight(self, mode: str) -> float:
        """
        Return the  weight based on cost function.
 
  
        time  → minimize total flight minutes
        cost  → minimize total ticket price (USD)
        connections  → minimize number of connections (weight = 1 per hop)
        """
        if mode == "time":
            return float(self.travel_time)
        if mode == "cost":
            return float(self.cost)
        if mode == "connections":
            return 1.0
        raise ValueError(f"Unknown optimization mode: '{mode}'. "
                         f"Choose 'time', 'cost', or 'connections'.")
 

#FLight grap: Add a node for each airport and a directed edge for each flight 
#Use dict since we want fast lookup and there is a one node for each airport 
 
class FlightGraph:
    """
    Weighted directed graph representing the airline route network.
 
    Representation : adjacency list
        _adj[origin_code] = [FlightEdge, FlightEdge, ...]
 
    Each FlightEdge stores TWO weights (travel_time and cost) so that
    the same graph structure can serve all three optimization modes
    without duplication. 

    """
 
    def __init__(self):
        self._adj: dict[str, list[FlightEdge]] = {}
        self._edge_count: int = 0
 
    #add airport node 
 
    def add_node(self, code: str) -> None:
        """Register an airport node. No-op if already present."""
        code = code.upper()
        if code not in self._adj:
            self._adj[code] = []

    def remove_node(self, code: str) -> bool:
        """Remove an airport node and all its outgoing edges. Returns True if it existed."""
        code = code.upper()
        if code in self._adj:
            # Remove all outgoing edges from this node
            self._edge_count -= len(self._adj[code])
            del self._adj[code]
            # Also remove any edges pointing to this node
            incoming_removed = 0
            for edges in self._adj.values():
                before = len(edges)
                edges[:] = [e for e in edges if e.destination != code]
                incoming_removed += before - len(edges)
            self._edge_count -= incoming_removed
            return True
        return False

    #Add directed edge between airports 
 
    def add_edge(self, origin: str, destination: str,
                 travel_time: int, cost: float, flight_id: str) -> None:
        """
        Add a directed flight edge origin → destination.
        creates nodes for both airports if not already present.
        """
        origin      = origin.upper()
        destination = destination.upper()
        self.add_node(origin)
        self.add_node(destination)
        edge = FlightEdge(destination, travel_time, cost, flight_id)
        self._adj[origin].append(edge)
        self._edge_count += 1

    #Remove edge by flight id
 
    def remove_edge(self, origin: str, flight_id: str) -> bool:
        """Remove the first edge with the given flight_id from origin."""
        origin = origin.upper()
        edges = self._adj.get(origin, [])
        for i, e in enumerate(edges):
            if e.flight_id == flight_id:
                edges.pop(i)
                self._edge_count -= 1
                return True
        return False
    
    #Return all edges from a given airport node
 
 
    def neighbors(self, code: str) -> list[FlightEdge]:
        """Return all outgoing FlightEdge objects from the given airport."""
        return self._adj.get(code.upper(), [])

    def get_edge(self, origin: str, destination: str) -> Optional[FlightEdge]:
        """Return the edge for origin → destination, or None if not present."""
        origin = origin.upper()
        destination = destination.upper()
        for edge in self._adj.get(origin, []):
            if edge.destination == destination:
                return edge
        return None

    def remove_edge_by_destination(self, origin: str, destination: str) -> bool:
        """Remove the edge origin → destination. Assumes at most one such edge exists."""
        origin = origin.upper()
        destination = destination.upper()
        edges = self._adj.get(origin, [])
        for i, edge in enumerate(edges):
            if edge.destination == destination:
                edges.pop(i)
                self._edge_count -= 1
                return True
        return False
    
    #Check if airport node exists in the graph
 
    def has_node(self, code: str) -> bool:
        return code.upper() in self._adj
    
    #Return all airport nodes in the graph
 
    def all_nodes(self) -> list[str]:
        return list(self._adj.keys())
 
    @property
    def node_count(self) -> int:
        return len(self._adj)
 
    @property
    def edge_count(self) -> int:
        return self._edge_count
    
    #Print stats, total number of nodes equals total number of airports, total number of edges equals total number of flights
   
    def summary(self) -> dict:
        """Return basic graph statistics."""
        return {
            "nodes":      self.node_count,
            "edges":      self.edge_count,
        }
 

#Structures for route calculation algorithm 
#A min-heap structure based on the accumulated weights of the partial routes is the base for the route calculation
# Node for the heap 
#Key: airport code
#Weight: accumulated cost/time/connections to reach this node from the origin
#Path: list of IATA codes representing the path taken to reach this node, assume only one path connects two nodes directly




class MinHeap:
    """
    Min-heap priority queue for route calculation.
    Each element is a tuple of (weight, airport_code, path).
    The heap is implemented as a list, and the hash table maps airport codes to their index in the heap for O(1) access during key updates.
    """
    def __init__(self, initial_data=None):
        self.heap = [] #List of tuples (weight, airport_code, path)
        self.size = 0
        #If initial data is provided, insert it into the heap
        #initial_data is a list of tuples (weight, airport_code, path)
        if initial_data is not None:
            for element in initial_data:
                self.insert(element[0], element[1], element[2])
    
    #Decrese key function: Update the weight of an element in the heap and maintain the heap priority
    def decrease_key(self, index, new_weight):
        airport_code = self.heap[index][1]
        path = self.heap[index][2]
        self.heap[index] = (new_weight, airport_code, path)
        while index > 0:
            parent_index = (index - 1) // 2
            if self.heap[index][0] >= self.heap[parent_index][0]:
                break
            self.heap[index], self.heap[parent_index] = self.heap[parent_index], self.heap[index]
            index = parent_index
    #insert function: First insert it in the heap array and return the index, then maintain the heap property by decreasing the key
    # new element is always inserted at the end of the heap array, then we decrease the key to maintain the heap property
    def insert(self, weight, airport_code, path):
        self.heap.append((weight, airport_code, path))
        self.size += 1
        self.decrease_key(self.size - 1, weight)

    #extract min function: Remove and return the element with the smallest weight (the root of the heap), then maintain the heap property by decreasing the key of the last element and heapifying the root
    # Return the airport code, weight, and path of the extracted element
    def extract_min(self):
        if self.size == 0:
            return None #Heap is empty
        min_element = self.heap[0]
        last_element = self.heap.pop()
        self.size -= 1
        if self.size > 0:
            self.heap[0] = last_element
            self.heapify(self.heap, self.size, 0)
        weight, airport_code, path = min_element[0], min_element[1], min_element[2]
        return airport_code, weight, path #Return the airport code, weight, and path of the extracted element     
    
    #increase key function: Update the weight of an element in the heap and maintain the heap priority
    def increase_key_element(self, index, new_weight):
        #Update the weight in the heap array
        airport_code = self.heap[index][1]
        path = self.heap[index][2]
        self.heap[index] = (new_weight, airport_code, path)
        #Heapify the element at the given index to maintain the heap property
        self.heapify(self.heap, self.size, index)
    
    #decrease key function: Update the weight of an element in the heap and maintain the heap priority
    def decrease_key_element(self, index, new_weight):
        #Update the weight in the heap array
        airport_code = self.heap[index][1]
        path = self.heap[index][2]
        self.heap[index] = (new_weight, airport_code, path)
        #Decrease the key of the element at the given index to maintain the heap property
        self.decrease_key(index, new_weight)

    #Check if the heap is empty
    def is_empty(self):
        return self.size == 0
    
    #Heapify function: Maintain the heap property by heapifying the element at the given index
    def heapify(self, arr, n, i):
        #Start with i as the smallest element (the element to be heapified)
        smallest = i 
        l = 2 * i + 1 # left = 2*i + 1
        r = 2 * i + 2 # right = 2*i + 2

        
        # If left child is smaller than root
        if l < n and arr[l][0] < arr[smallest][0]:
            smallest = l

        # If right child is smaller than smallest so far
        if r < n and arr[r][0] < arr[smallest][0]:
            smallest = r

        # If smallest is not root
        if smallest != i:
            # Swap elements in heap
            tmp_val = arr[i]
            arr[i] = arr[smallest]
            arr[smallest] = tmp_val
            
            #smallest keeps the swapped element's index, so we need to heapify the affected sub-tree
            self.heapify(arr, n, smallest)


#Initial route calculation algorithm: Dijkstra's algorithm using the MinHeap for the priority queue and the FlightGraph for the graph representation.
# The algorithm will be implemented in a separate function that takes the FlightGraph,  origin code, destination code, and optimization mode as input and returns the optimal route and its total weight.

def RouteCalculation(
    graph: FlightGraph,
    origin: str,
    destination: str,
    mode: str,
    blocked_nodes: Optional[set[str]] = None,
    blocked_edges: Optional[set[tuple[str, str]]] = None,
    verbose: bool = True,
) -> Optional[tuple[float, list[str]]]:
    """
    Calculate the optimal route from origin to destination based on the given optimization mode.
    Returns a tuple of (total_weight, path) where total_weight is the accumulated weight of the optimal route and path is a list of IATA codes representing the route taken.
    If no route exists, returns None.
    """

    destination = destination.upper()
    origin = origin.upper()
    blocked_nodes = {node.upper() for node in (blocked_nodes or set())}
    blocked_edges = {
        (edge_origin.upper(), edge_destination.upper())
        for edge_origin, edge_destination in (blocked_edges or set())
    }

    if origin in blocked_nodes or destination in blocked_nodes:
        return None

    #Check if origin and destination airports exist in the graph
    if not graph.has_node(origin):
        if verbose:
            print(f"Origin airport '{origin}' does not exist in the graph.")
        return None
    if not graph.has_node(destination):
        if verbose:
            print(f"Destination airport '{destination}' does not exist in the graph.")
        return None

    if mode == "time":
        edge_weight_fn = lambda edge: float(edge.travel_time)
    elif mode == "cost":
        edge_weight_fn = lambda edge: float(edge.cost)
    elif mode == "connections":
        edge_weight_fn = lambda edge: 1.0
    else:
        raise ValueError(f"Unknown optimization mode: '{mode}'. "
                         f"Choose 'time', 'cost', or 'connections'.")

    # Dijkstra with custom MinHeap + predecessor map avoids per-edge path copies.
    best_weight: dict[str, float] = {origin: 0.0}
    predecessor: dict[str, str] = {}
    min_heap = MinHeap()
    min_heap.insert(0.0, origin, None)

    while not min_heap.is_empty():
        extracted = min_heap.extract_min()
        if extracted is None:
            break
        current_airport, current_weight, _ = extracted

        if current_weight != best_weight.get(current_airport, float("inf")):
            continue

        if current_airport == destination:
            path = [destination]
            while path[-1] != origin:
                path.append(predecessor[path[-1]])
            path.reverse()
            return current_weight, path

        for edge in graph.neighbors(current_airport):
            next_airport = edge.destination
            if next_airport in blocked_nodes:
                continue
            if (current_airport, next_airport) in blocked_edges:
                continue
            new_weight = current_weight + edge_weight_fn(edge)

            if new_weight < best_weight.get(next_airport, float("inf")):
                best_weight[next_airport] = new_weight
                predecessor[next_airport] = current_airport
                min_heap.insert(new_weight, next_airport, None)
    
    #If we exhaust the heap without reaching the destination, it means there is no route available
    if verbose:
        print(f"No route found from '{origin}' to '{destination}'.")
    return None



#Find the shortest k routes function. Using Yen's K-Shortest paths algorithm
def yen_k_shortest(graph: FlightGraph, origin: str, destination: str,
                   mode: str, k: int = 3) -> list[tuple[float, list[str]]]:
    """
    Yen's K-Shortest Paths algorithm 
    Returns up to k routes sorted ascending by total weight.
    #Input: graph, origin code, destination code, optimization mode, and number of routes to return (k)
    #Output: list of tuples (total_weight, path, flight_ids) where total_weight is the accumulated weight of the route, path is a list of IATA codes representing the route taken, and flight_ids is a list of flight IDs corresponding to each leg of the route.

    """
    origin      = origin.upper()
    destination = destination.upper()

    def _path_weight(path: list[str]) -> Optional[float]:
        total = 0.0
        for i in range(len(path) - 1):
            edge = graph.get_edge(path[i], path[i + 1])
            if edge is None:
                return None
            total += edge.weight(mode)
        return total

    # A: confirmed k-shortest paths
    # B: candidate paths (min-heap)
    A: list[tuple[float, list[str]]] = []
    B: list[tuple[float, int, list[str]]] = []  # (cost, seq, path)
    seen_paths: set[tuple[str, ...]] = set()
    candidate_paths: set[tuple[str, ...]] = set()
    seq = 0

    #First, find the single shortest path from origin to destination using Dijkstra's algorithm
    result = RouteCalculation(graph, origin, destination, mode)

    if result is None:
        return A  # No path exists, return empty list
    
    A.append(result)
    seen_paths.add(tuple(result[1]))

    #Iteratively find the next k-1 shortest paths
    for k_i in range(1, k):
        #The spur node ranges from the first node to the second-to-last node in the previous shortest path
        for i in range(len(A[k_i - 1][1]) - 1):
            spur_node = A[k_i - 1][1][i]
            #From origin to spur node
            root_path = A[k_i - 1][1][:i + 1]

            blocked_edges: set[tuple[str, str]] = set()
            for _, confirmed_path in A:
                if len(confirmed_path) > i and confirmed_path[:i + 1] == root_path:
                    blocked_edges.add((confirmed_path[i], confirmed_path[i + 1]))

            blocked_nodes = set(root_path[:-1])

            #Calculate the spur path from the spur node to the destination
            spur_result = RouteCalculation(
                graph,
                spur_node,
                destination,
                mode,
                blocked_nodes=blocked_nodes,
                blocked_edges=blocked_edges,
                verbose=False,
            )

            if spur_result is not None:
                _, spur_path = spur_result
                total_path = root_path[:-1] + spur_path
                path_key = tuple(total_path)
                if path_key in seen_paths or path_key in candidate_paths:
                    continue

                total_weight = _path_weight(total_path)
                if total_weight is None:
                    continue

                heapq.heappush(B, (total_weight, seq, total_path))
                seq += 1
                candidate_paths.add(path_key)
            
        if not B:
            break  # No more candidates, exit the loop

        best_weight, _, best_path = heapq.heappop(B)
        best_key = tuple(best_path)
        candidate_paths.discard(best_key)
        A.append((best_weight, best_path))
        seen_paths.add(best_key)
    
    return A




    

    


#Entry 
#The program takes the following argments:
# 1. A list of airports with their metadata (code, name, city, country)
# Format: ident,type,name,elevation_ft,continent,iso_country,iso_region,municipality,icao_code,iata_code,gps_code,local_code,coordinates
# 2. A list of flights with their details (origin code, destination code, travel time, cost, flight id)
# Format: flight_id,origin_code,destination_code,travel_time,cost
#Then, it prompts the user to input the origin and destination airports (by code, name, or city) and the optimization mode (time, cost, or connections), and it calculates and displays the optimal route based on the user's input.

if __name__ == "__main__":
    import csv
    import sys
    import os
    import argparse
    #Parse command-line arguments for input files
    parser = argparse.ArgumentParser(description="Flight Booking & Route Optimization System")
    parser.add_argument("--airports", required=True, help="Path to the airports CSV file")
    parser.add_argument("--flights", required=True, help="Path to the flights CSV file")
    args = parser.parse_args()

    #Check if input files exist and the headers are in the expected format. If not, print an error message and exit.
    if not os.path.isfile(args.airports):
        print(f"Error: Airports file '{args.airports}' does not exist.")
        sys.exit(1)
    else:
        with open(args.airports, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader, None)
            expected_headers = ['ident', 'type', 'name', 'elevation_ft', 'continent', 'iso_country', 'iso_region', 'municipality', 'icao_code', 'iata_code', 'gps_code', 'local_code', 'coordinates']
            if headers != expected_headers:
                print(f"Error: Airports file '{args.airports}' has incorrect headers. Expected: {expected_headers}")
                sys.exit(1)

    
    if not os.path.isfile(args.flights):
        print(f"Error: Flights file '{args.flights}' does not exist.")
        sys.exit(1)
    else:
        with open(args.flights, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader, None)
            expected_headers = ['flight_id', 'origin_code', 'destination_code', 'travel_time', 'cost']
            if headers != expected_headers:
                print(f"Error: Flights file '{args.flights}' has incorrect headers. Expected: {expected_headers}")
                sys.exit(1)
    
    #Initialize the airport registry and flight graph
    airport_registry = AirportRegistry()
    flight_graph = FlightGraph()

    #Load airports from the CSV file into the airport registry
    with open(args.airports, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            code = row['iata_code']
            name = row['name']
            city = row['municipality']
            country = row['iso_country']
            if code: #Only add airports with a valid IATA code
                airport_registry.add_airport(code, name, city, country)
    
    #Load flights from the CSV file into the flight graph
    with open(args.flights, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            flight_id = row['flight_id']
            origin_code = row['origin_code']
            destination_code = row['destination_code']
            travel_time = int(row['travel_time'])
            cost = float(row['cost'])
            flight_graph.add_edge(origin_code, destination_code, travel_time, cost, flight_id)

    #Prompt the user for input and calculate the optimal route
    #After every query, the user can choose to make another query or exit the program. 

    exit_program = False
    while not exit_program:

        #Select the origin airport by code, name, or city. If multiple matches are found, prompt the user to disambiguate by selecting from a list of matches.
        
        valid_input = False
        while not valid_input:
            origin_input = input("Enter the origin airport (code, name, or city): ")
            origin_codes = airport_registry.get_codes_by_name(origin_input) + airport_registry.get_codes_by_city(origin_input) + [(code, *airport_registry.get_airport(code)) for code in airport_registry.all_codes() if code == origin_input.upper()]
            if not origin_codes:
                print(f"No airports found matching '{origin_input}'. Please try again.")
            else:
                valid_input = True
                if len(origin_codes) > 1:
                    print(f"Multiple airports found matching '{origin_input}':")
                    for i, (code, name, city, country) in enumerate(origin_codes):
                        print(f"{i + 1}. {code} - {name}, {city}, {country}")
                    selected_index = -1

                    valid_input_selected = False
                    while not valid_input_selected:
                        try:
                            selected_index = int(input("Select the number corresponding to the correct origin airport: ")) - 1
                            if 0 <= selected_index < len(origin_codes):
                                valid_input_selected = True
                            else:
                                print("Invalid selection. Please enter a number from the list.")
                        except ValueError:
                            print("Invalid selection. Please enter a number from the list.")
                    origin_code = origin_codes[selected_index][0]
                
                else:
                    origin_code = origin_codes[0][0]
        
        print(f"Selected origin airport: {airport_registry.get_airport(origin_code)[0]} - {airport_registry.get_airport(origin_code)[1]}, {airport_registry.get_airport(origin_code)[2]}, {origin_code}")        
        

        #Select the destination airport by code, name, or city. If multiple matches are found, prompt the user to disambiguate by selecting from a list of matches.
        valid_input = False
        while not valid_input:
            destination_input = input("Enter the destination airport (code, name, or city): ")
            destination_codes = airport_registry.get_codes_by_name(destination_input) + airport_registry.get_codes_by_city(destination_input) + [(code, *airport_registry.get_airport(code)) for code in airport_registry.all_codes() if code == destination_input.upper()]
            if not destination_codes:
                print(f"No airports found matching '{destination_input}'. Please try again.")
            else:
                valid_input = True
                if len(destination_codes) > 1:
                    print(f"Multiple airports found matching '{destination_input}':")
                    for i, (code, name, city, country) in enumerate(destination_codes):
                        print(f"{i + 1}. {code} - {name}, {city}, {country}")
                    selected_index = -1

                    valid_input_selected = False
                    while not valid_input_selected:
                        try:
                            selected_index = int(input("Select the number corresponding to the correct destination airport: ")) - 1
                            if 0 <= selected_index < len(destination_codes):
                                valid_input_selected = True
                            else:
                                print("Invalid selection. Please enter a number from the list.")
                        except ValueError:
                            print("Invalid selection. Please enter a number from the list.")
                    destination_code = destination_codes[selected_index][0]
                
                else:
                    destination_code = destination_codes[0][0]
        
        print(f"Selected destination airport: {airport_registry.get_airport(destination_code)[0]} - {airport_registry.get_airport(destination_code)[1]}, {airport_registry.get_airport(destination_code)[2]}, {destination_code}")

        #Select the optimization mode (time, cost, or connections)
        valid_input = False
        while not valid_input:
            optimization_mode = input("Select what you prefer to prioritize (time, cost, connections): ").strip().lower()
            if optimization_mode in ['time', 'cost', 'connections']:
                valid_input = True
            else:
                print("Invalid input. Please enter 'time', 'cost', or 'connections'.")

        #At this point all inputs have been successfully validated and data is ready, proceed with route calculation

        #Ask user how many routes they want to see, default to 3 if they just press enter. If the input is not a valid integer, prompt them again until they provide a valid input.
        valid_input = False
        while not valid_input:
            k_input = input("How many routes do you want to see? (default 3): ").strip()
            if k_input == "":
                k = 3
                valid_input = True
            else:
                try:
                    k = int(k_input)
                    if k > 0:
                        valid_input = True
                    else:
                        print("Please enter a positive integer.")
                except ValueError:
                    print("Invalid input. Please enter a valid integer.")
        
        #Calculate the optimal routes using Yen's K-Shortest Paths algorithm
        routes = yen_k_shortest(flight_graph, origin_code, destination_code, optimization_mode, k)

        #Calculate the optimal route using the RouteCalculation function
        #result = RouteCalculation(flight_graph, origin_code, destination_code, optimization_mode)

        if len(routes) > 0:
            #Calculate the missing costs for each route to present to the user, since the RouteCalculation function only returns the total weight based on the optimization mode, we need to calculate the other weights for presentation purposes
            routes_with_costs = []
            for total_weight, path in routes:
                total_time = 0
                total_cost = 0.0
                leg_edges: list[FlightEdge] = []
                valid_path = True
                for j in range(len(path) - 1):
                    edge = flight_graph.get_edge(path[j], path[j + 1])
                    if edge is None:
                        valid_path = False
                        break
                    leg_edges.append(edge)
                    total_time += edge.travel_time
                    total_cost += edge.cost

                if not valid_path:
                    continue
                #Total connections
                if len(path) > 2:
                    total_connections = len(path) - 2 #Number of connections is number of stops minus 1 (since the first stop is the origin and the last stop is the destination)
                
                else:
                    total_connections = 0 #Direct flight, no connections

                routes_with_costs.append((total_weight, path, total_time, total_cost, total_connections, leg_edges))
            print(f"Top {len(routes)} optimal routes from '{origin_code}' to '{destination_code}' prioritizing {optimization_mode}:")
            for i, (total_weight, path, total_time, total_cost, total_connections, leg_edges) in enumerate(routes_with_costs):
                print(f"Itinerary {i + 1}: {' -> '.join(path)}")
                print(f"Total travel time: {total_time} minutes")
                print(f"Total cost: ${total_cost:.2f}")
                print(f"Total connections: {total_connections}")
                print("------------------------------------")
                #Print the detailed route with airport codes and individual costs and times for each leg of the route
                print("Detailed route:")
                for j in range(len(path) - 1):
                    origin = path[j]
                    destination = path[j + 1]
                    edge = leg_edges[j]
                    print(f"{origin} -> {destination}: Flight ID {edge.flight_id}, Travel Time {edge.travel_time} minutes, Cost ${edge.cost:.2f}")

        else:
            print("No routes found.")



        #Ask the user if they want to make another query or exit the program
        valid_input = False
        while not valid_input:
            continue_input = input("Do you want to make another query? (yes/no): ").strip().lower()
            if continue_input in ['yes', 'y']:
                valid_input = True
            elif continue_input in ['no', 'n']:
                valid_input = True
                exit_program = True
            else:
                print("Invalid input. Please enter 'yes' or 'no'.")

        


    

    
















 
 
