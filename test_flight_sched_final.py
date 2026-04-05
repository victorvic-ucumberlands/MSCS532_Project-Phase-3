import csv
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from flight_sched_final import (
    AirportRegistry,
    FlightGraph,
    MinHeap,
    RouteCalculation,
    yen_k_shortest,
)


ROOT = Path(__file__).resolve().parent
SCRIPT_PATH = ROOT / "flight_sched_final.py"


def build_sample_graph() -> FlightGraph:
    graph = FlightGraph()
    graph.add_edge("AAA", "CCC", 50, 500.0, "F3")
    graph.add_edge("AAA", "BBB", 10, 10.0, "F1")
    graph.add_edge("BBB", "DDD", 10, 10.0, "F2")
    graph.add_edge("CCC", "DDD", 100, 100.0, "F4")
    graph.add_edge("AAA", "DDD", 60, 5.0, "F5")
    return graph


class AirportRegistryTests(unittest.TestCase):
    def test_add_get_exists_and_remove_are_case_insensitive(self):
        registry = AirportRegistry()
        registry.add_airport("abc", "Alpha Airport", "Madison", "US")

        self.assertTrue(registry.exists("ABC"))
        self.assertEqual(registry.get_airport("ABC"), ("Alpha Airport", "Madison", "US"))
        self.assertTrue(registry.remove_airport("AbC"))
        self.assertFalse(registry.remove_airport("ABC"))
        self.assertIsNone(registry.get_airport("ABC"))

    def test_reverse_lookup_escapes_regex_characters(self):
        registry = AirportRegistry()
        registry.add_airport("A1", "A+B (Test)", "Metro[One]", "US")
        registry.add_airport("A2", "Plain Airport", "Elsewhere", "US")

        name_matches = registry.get_codes_by_name("A+B (")
        city_matches = registry.get_codes_by_city("Metro[")

        self.assertEqual([match[0] for match in name_matches], ["A1"])
        self.assertEqual([match[0] for match in city_matches], ["A1"])

    def test_all_codes_and_all_airports_return_registered_items(self):
        registry = AirportRegistry()
        registry.add_airport("AAA", "Alpha", "One", "US")
        registry.add_airport("BBB", "Beta", "Two", "US")

        self.assertCountEqual(registry.all_codes(), ["AAA", "BBB"])
        self.assertCountEqual(
            registry.all_airports(),
            [
                ("AAA", ("Alpha", "One", "US")),
                ("BBB", ("Beta", "Two", "US")),
            ],
        )


class FlightGraphTests(unittest.TestCase):
    def test_add_edge_creates_nodes_and_summary_counts(self):
        graph = FlightGraph()
        graph.add_edge("aaa", "bbb", 45, 99.0, "AB1")

        self.assertTrue(graph.has_node("AAA"))
        self.assertTrue(graph.has_node("BBB"))
        self.assertEqual(graph.node_count, 2)
        self.assertEqual(graph.edge_count, 1)
        self.assertEqual(graph.summary(), {"nodes": 2, "edges": 1})

    def test_get_edge_and_remove_edge_by_destination(self):
        graph = FlightGraph()
        graph.add_edge("AAA", "BBB", 45, 99.0, "AB1")

        edge = graph.get_edge("AAA", "BBB")
        self.assertIsNotNone(edge)
        self.assertEqual(edge.flight_id, "AB1")
        self.assertTrue(graph.remove_edge_by_destination("AAA", "BBB"))
        self.assertIsNone(graph.get_edge("AAA", "BBB"))
        self.assertEqual(graph.edge_count, 0)
        self.assertFalse(graph.remove_edge_by_destination("AAA", "BBB"))

    def test_remove_edge_by_flight_id_updates_count(self):
        graph = FlightGraph()
        graph.add_edge("AAA", "BBB", 45, 99.0, "AB1")
        graph.add_edge("AAA", "CCC", 50, 109.0, "AC1")

        self.assertTrue(graph.remove_edge("AAA", "AB1"))
        self.assertEqual(graph.edge_count, 1)
        self.assertFalse(graph.remove_edge("AAA", "AB1"))

    def test_remove_node_removes_incoming_and_outgoing_edges(self):
        graph = FlightGraph()
        graph.add_edge("AAA", "BBB", 10, 10.0, "AB1")
        graph.add_edge("BBB", "CCC", 20, 20.0, "BC1")
        graph.add_edge("AAA", "CCC", 30, 30.0, "AC1")

        self.assertTrue(graph.remove_node("BBB"))
        self.assertFalse(graph.has_node("BBB"))
        self.assertEqual(graph.edge_count, 1)
        self.assertIsNone(graph.get_edge("AAA", "BBB"))
        self.assertIsNone(graph.get_edge("BBB", "CCC"))
        remaining_edge = graph.get_edge("AAA", "CCC")
        self.assertIsNotNone(remaining_edge)
        self.assertFalse(graph.remove_node("BBB"))


class MinHeapTests(unittest.TestCase):
    def test_extract_min_returns_items_in_weight_order(self):
        heap = MinHeap()
        heap.insert(5.0, "EEE", ["EEE"])
        heap.insert(2.0, "BBB", ["BBB"])
        heap.insert(3.0, "CCC", ["CCC"])

        self.assertEqual(heap.extract_min(), ("BBB", 2.0, ["BBB"]))
        self.assertEqual(heap.extract_min(), ("CCC", 3.0, ["CCC"]))
        self.assertEqual(heap.extract_min(), ("EEE", 5.0, ["EEE"]))
        self.assertIsNone(heap.extract_min())

    def test_decrease_and_increase_key_preserve_heap_invariants(self):
        heap = MinHeap()
        heap.insert(5.0, "EEE", ["EEE"])
        heap.insert(7.0, "GGG", ["GGG"])
        heap.insert(9.0, "III", ["III"])

        heap.decrease_key_element(2, 1.0)
        self.assertEqual(heap.extract_min(), ("III", 1.0, ["III"]))

        heap.increase_key_element(0, 10.0)
        self.assertEqual(heap.extract_min(), ("GGG", 7.0, ["GGG"]))
        self.assertEqual(heap.extract_min(), ("EEE", 10.0, ["EEE"]))


class RouteCalculationTests(unittest.TestCase):
    def test_route_calculation_chooses_fastest_path(self):
        graph = build_sample_graph()

        result = RouteCalculation(graph, "aaa", "ddd", "time", verbose=False)

        self.assertEqual(result, (20.0, ["AAA", "BBB", "DDD"]))

    def test_route_calculation_chooses_cheapest_path(self):
        graph = build_sample_graph()

        result = RouteCalculation(graph, "AAA", "DDD", "cost", verbose=False)

        self.assertEqual(result, (5.0, ["AAA", "DDD"]))

    def test_route_calculation_chooses_fewest_connections(self):
        graph = build_sample_graph()

        result = RouteCalculation(graph, "AAA", "DDD", "connections", verbose=False)

        self.assertEqual(result, (1.0, ["AAA", "DDD"]))

    def test_route_calculation_respects_blocked_edges_and_nodes(self):
        graph = build_sample_graph()

        rerouted = RouteCalculation(
            graph,
            "AAA",
            "DDD",
            "time",
            blocked_edges={("AAA", "BBB")},
            verbose=False,
        )
        blocked = RouteCalculation(
            graph,
            "AAA",
            "DDD",
            "time",
            blocked_nodes={"BBB", "CCC", "DDD"},
            verbose=False,
        )

        self.assertEqual(rerouted, (60.0, ["AAA", "DDD"]))
        self.assertIsNone(blocked)

    def test_route_calculation_returns_none_for_unreachable_or_missing_nodes(self):
        graph = FlightGraph()
        graph.add_edge("AAA", "BBB", 10, 10.0, "AB1")

        self.assertIsNone(RouteCalculation(graph, "AAA", "CCC", "time", verbose=False))
        self.assertIsNone(RouteCalculation(graph, "ZZZ", "BBB", "time", verbose=False))

    def test_route_calculation_raises_for_invalid_mode(self):
        graph = build_sample_graph()

        with self.assertRaises(ValueError):
            RouteCalculation(graph, "AAA", "DDD", "distance", verbose=False)


class YenKShortestTests(unittest.TestCase):
    def build_yen_graph(self) -> FlightGraph:
        graph = FlightGraph()
        graph.add_edge("A", "B", 1, 1.0, "AB")
        graph.add_edge("B", "D", 1, 1.0, "BD")
        graph.add_edge("A", "C", 1, 1.0, "AC")
        graph.add_edge("C", "D", 1, 1.0, "CD")
        graph.add_edge("A", "E", 2, 2.0, "AE")
        graph.add_edge("E", "D", 1, 1.0, "ED")
        graph.add_edge("A", "D", 5, 5.0, "AD")
        return graph

    def test_yen_returns_unique_paths_in_nondecreasing_weight_order(self):
        graph = self.build_yen_graph()

        routes = yen_k_shortest(graph, "A", "D", "time", 4)

        self.assertEqual(
            routes,
            [
                (2.0, ["A", "B", "D"]),
                (2.0, ["A", "C", "D"]),
                (3.0, ["A", "E", "D"]),
                (5.0, ["A", "D"]),
            ],
        )

    def test_yen_returns_all_available_routes_when_k_is_large(self):
        graph = self.build_yen_graph()

        routes = yen_k_shortest(graph, "A", "D", "time", 10)

        self.assertEqual(len(routes), 4)
        self.assertEqual(len({tuple(path) for _, path in routes}), 4)

    def test_yen_returns_empty_list_when_no_route_exists(self):
        graph = FlightGraph()
        graph.add_edge("A", "B", 1, 1.0, "AB")

        with redirect_stdout(io.StringIO()):
            self.assertEqual(yen_k_shortest(graph, "A", "D", "time", 3), [])


class CommandLineIntegrationTests(unittest.TestCase):
    def write_airports_csv(self, path: Path):
        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "ident",
                "type",
                "name",
                "elevation_ft",
                "continent",
                "iso_country",
                "iso_region",
                "municipality",
                "icao_code",
                "iata_code",
                "gps_code",
                "local_code",
                "coordinates",
            ])
            writer.writerow(["AAA1", "small_airport", "Alpha Airport", 0, "NA", "US", "US-WI", "Madison", "", "AAA", "", "", "0,0"])
            writer.writerow(["BBB1", "small_airport", "Beta Airport", 0, "NA", "US", "US-WI", "Milwaukee", "", "BBB", "", "", "0,0"])
            writer.writerow(["CCC1", "small_airport", "Gamma Airport", 0, "NA", "US", "US-WI", "Chicago", "", "CCC", "", "", "0,0"])
            writer.writerow(["DDD1", "small_airport", "Delta Airport", 0, "NA", "US", "US-WI", "Green Bay", "", "DDD", "", "", "0,0"])

    def write_flights_csv(self, path: Path):
        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["flight_id", "origin_code", "destination_code", "travel_time", "cost"])
            writer.writerow(["F3", "AAA", "CCC", 50, 500.0])
            writer.writerow(["F1", "AAA", "BBB", 10, 10.0])
            writer.writerow(["F2", "BBB", "DDD", 10, 10.0])
            writer.writerow(["F4", "CCC", "DDD", 100, 100.0])
            writer.writerow(["F5", "AAA", "DDD", 60, 5.0])

    def test_cli_happy_path_prints_expected_itinerary_and_leg_details(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            airports_path = tmp_path / "airports.csv"
            flights_path = tmp_path / "flights.csv"
            self.write_airports_csv(airports_path)
            self.write_flights_csv(flights_path)

            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--airports",
                    str(airports_path),
                    "--flights",
                    str(flights_path),
                ],
                input="AAA\nDDD\ntime\n2\nno\n",
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(process.returncode, 0, msg=process.stderr)
            self.assertIn("Top 2 optimal routes from 'AAA' to 'DDD' prioritizing time:", process.stdout)
            self.assertIn("Itinerary 1: AAA -> BBB -> DDD", process.stdout)
            self.assertIn("Flight ID F1", process.stdout)
            self.assertIn("Flight ID F2", process.stdout)

    def test_cli_rejects_invalid_flight_headers(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            airports_path = tmp_path / "airports.csv"
            flights_path = tmp_path / "flights.csv"
            self.write_airports_csv(airports_path)

            with open(flights_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["bad", "header"])

            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--airports",
                    str(airports_path),
                    "--flights",
                    str(flights_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(process.returncode, 0)
            self.assertIn("has incorrect headers", process.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)