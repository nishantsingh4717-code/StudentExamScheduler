
from flask import Flask, render_template, request
from collections import defaultdict
from datetime import datetime, timedelta
import time
import os
import networkx as nx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)

SLOT_NAMES = [
    "09:00 AM - 12:00 PM",
    "02:00 PM - 05:00 PM"
]


def build_conflict_graph(enrollments):
    graph = defaultdict(set)
    subjects = list(enrollments.keys())

    for subject in subjects:
        graph[subject]

    for i in range(len(subjects)):
        for j in range(i + 1, len(subjects)):
            first = subjects[i]
            second = subjects[j]

            if set(enrollments[first]) & set(enrollments[second]):
                graph[first].add(second)
                graph[second].add(first)

    return graph


def greedy_graph_coloring(graph):
    colors = {}

    order = sorted(
        graph,
        key=lambda subject: len(graph[subject]),
        reverse=True
    )

    for subject in order:
        unavailable = {
            colors[neighbor]
            for neighbor in graph[subject]
            if neighbor in colors
        }

        color = 0

        while color in unavailable:
            color += 1

        colors[subject] = color

    return colors


def generate_conflict_graph_image(graph, colors):
    if not graph:
        return False

    os.makedirs(app.static_folder, exist_ok=True)

    graph_image_path = os.path.join(
        app.static_folder,
        "conflict_graph.png"
    )

    G = nx.Graph()

    for subject in graph:
        G.add_node(subject)

    for subject in graph:
        for neighbor in graph[subject]:
            G.add_edge(subject, neighbor)

    positions = nx.spring_layout(G, seed=42)

    node_colors = [
        colors[node] for node in G.nodes()
    ]

    plt.figure(figsize=(11, 7))

    nx.draw_networkx(
        G,
        positions,
        with_labels=True,
        node_color=node_colors,
        cmap=plt.cm.Set3,
        node_size=2500,
        font_size=9,
        font_weight="bold",
        edge_color="#64748b",
        width=1.5
    )

    plt.title("Student Exam Conflict Graph", fontsize=15)
    plt.axis("off")
    plt.tight_layout()

    plt.savefig(
        graph_image_path,
        dpi=160,
        bbox_inches="tight"
    )

    plt.close()

    return True


@app.route("/", methods=["GET", "POST"])
def index():
    schedule = []
    error = None
    stats = None
    conflicts = []
    graph_image = False

    if request.method == "POST":
        raw_data = request.form.get("enrollments", "").strip()
        start_date_input = request.form.get("start_date", "")

        enrollments = {}

        try:
            for line in raw_data.splitlines():
                if not line.strip():
                    continue

                parts = line.split(":", 1)

                if len(parts) != 2:
                    raise ValueError(
                        "Format: SUBJECT: student IDs use karo."
                    )

                subject = parts[0].strip()

                students = [
                    student.strip()
                    for student in parts[1].split(",")
                    if student.strip()
                ]

                if not subject or not students:
                    raise ValueError(
                        "Har subject ke saath student IDs enter karo."
                    )

                if subject in enrollments:
                    raise ValueError(
                        "Duplicate subject: " + subject
                    )

                enrollments[subject] = students

            if len(enrollments) < 2:
                raise ValueError(
                    "Kam se kam 2 subjects enter karo."
                )

            if not start_date_input:
                raise ValueError(
                    "Please select the first exam date."
                )

            try:
                start_date = datetime.strptime(
                    start_date_input,
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                raise ValueError(
                    "Please enter a valid exam start date."
                )

            start_time = time.perf_counter()

            graph = build_conflict_graph(enrollments)
            colors = greedy_graph_coloring(graph)

            runtime = (
                time.perf_counter() - start_time
            ) * 1000

            for subject in graph:
                for neighbor in graph[subject]:
                    if subject < neighbor:
                        conflicts.append((subject, neighbor))

            graph_image = generate_conflict_graph_image(
                graph,
                colors
            )

            exams_per_day = len(SLOT_NAMES)

            for subject, color in sorted(
                colors.items(),
                key=lambda item: (item[1], item[0])
            ):
                day_number = color // exams_per_day + 1
                slot_number = color % exams_per_day

                exam_date = start_date + timedelta(
                    days=day_number - 1
                )

                schedule.append({
                    "subject": subject,
                    "day": day_number,
                    "date": exam_date.strftime("%d-%m-%Y"),
                    "slot": SLOT_NAMES[slot_number],
                    "students": len(enrollments[subject]),
                    "color": color
                })

            stats = {
                "subjects": len(enrollments),
                "conflicts": len(conflicts),
                "slots": max(colors.values()) + 1,
                "days": max(colors.values()) // exams_per_day + 1,
                "runtime": round(runtime, 3)
            }

        except ValueError as exc:
            error = str(exc)

    return render_template(
        "index.html",
        schedule=schedule,
        error=error,
        stats=stats,
        conflicts=conflicts,
        graph_image=graph_image
    )


if __name__ == "__main__":
    app.run(debug=True)
