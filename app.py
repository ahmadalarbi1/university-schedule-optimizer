import json
import pandas as pd
import streamlit as st
from typing import List, Dict, Set, Tuple

# Page layout setup
st.set_page_config(page_title="Schedule Optimizer", page_icon="📅", layout="wide")
st.title("📅 University Schedule Optimizer")
st.write("Find the optimal conflict-free schedule tailored to your preferences.")


# --- CORE OPTIMIZER CLASSES & LOGIC ---
class Schedule:
    DAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

    def __init__(self, schedule_data: list, class_code: str, source_mapping: dict = None):
        self.days = {day: {p: None for p in range(1, 7)} for day in self.DAYS}
        self.class_code = class_code
        self.source_mapping = source_mapping or {}
        
        for session in schedule_data:
            day = session["day"]
            period = session["period"]
            if day in self.days and period in self.days[day]:
                self.days[day][period] = {
                    "name": session["course_name"],
                    "code": session["course_code"],
                    "type": session["type"],
                    "instructor": session["instructor"]
                }

    def gaps(self) -> int:
        gaps_count = 0
        for day, periods in self.days.items():
            occupied = [p for p, s in periods.items() if s is not None]
            if len(occupied) > 1:
                span = max(occupied) - min(occupied) + 1
                gaps_count += (span - len(occupied))
        return gaps_count

    def days_occupied(self) -> List[str]:
        return [day for day, periods in self.days.items() if any(s is not None for s in periods.values())]

    def classes_per_day(self) -> Dict[str, int]:
        return {day: sum(1 for s in periods.values() if s is not None) for day, periods in self.days.items()}

    def max_classes_in_a_day(self) -> int:
        return max(self.classes_per_day().values(), default=0)


class CourseBundle:
    def __init__(self, course_code: str, course_name: str, source_class: str, sessions: list):
        self.course_code = course_code
        self.course_name = course_name
        self.source_class = source_class
        self.sessions = sessions
        self.slots = set((s["day"], s["period"]) for s in sessions)


def optimize_schedule(
    target_code: str, 
    file_names: list, 
    max_days: int = 4, 
    preferred_gaps: int = 0,
    max_classes_per_day: int = 4,
    excluded_instructors: List[str] = None
) -> List[Schedule]:
    
    excluded_instructors = [dr.lower().strip() for dr in (excluded_instructors or []) if dr]
    schedules_raw = {}
    for code in file_names:
        try:
            with open(f"{code}.json", encoding="utf-8") as f:
                schedules_raw[code] = json.load(f)
        except FileNotFoundError:
            continue

    if target_code not in schedules_raw:
        raise ValueError(f"Target schedule {target_code} not found.")

    target_sessions = schedules_raw[target_code]
    required_courses = sorted(list(set(s["course_code"] for s in target_sessions)))
    catalog: Dict[str, List[CourseBundle]] = {c: [] for c in required_courses}

    for class_code, sessions in schedules_raw.items():
        grouped = {}
        for s in sessions:
            c_code = s["course_code"]
            if c_code in required_courses:
                grouped.setdefault(c_code, []).append(s)

        for c_code, course_sessions in grouped.items():
            has_excluded_dr = any(
                any(ex in (s.get("instructor") or "").lower() for ex in excluded_instructors)
                for s in course_sessions
            )
            if has_excluded_dr:
                continue

            c_name = course_sessions[0]["course_name"]
            bundle = CourseBundle(c_code, c_name, class_code, course_sessions)
            if not any(b.slots == bundle.slots for b in catalog[c_code]):
                catalog[c_code].append(bundle)

    valid_schedules: List[Schedule] = []

    def backtrack(course_index: int, current_bundles: List[CourseBundle], occupied_slots: Set[Tuple[str, int]]):
        if course_index == len(required_courses):
            all_sessions = []
            source_map = {}
            for b in current_bundles:
                all_sessions.extend(b.sessions)
                source_map[b.course_code] = b.source_class
            valid_schedules.append(Schedule(all_sessions, "Optimized_Combination", source_mapping=source_map))
            return

        current_course = required_courses[course_index]
        for bundle in catalog[current_course]:
            if occupied_slots.isdisjoint(bundle.slots):
                new_slots = occupied_slots | bundle.slots
                day_counts: Dict[str, int] = {}
                for day, _ in new_slots:
                    day_counts[day] = day_counts.get(day, 0) + 1
                
                if len(day_counts) <= max_days and max(day_counts.values(), default=0) <= max_classes_per_day:
                    backtrack(course_index + 1, current_bundles + [bundle], new_slots)

    backtrack(0, [], set())
    valid_schedules.sort(key=lambda s: (len(s.days_occupied()), abs(s.gaps() - preferred_gaps), s.max_classes_in_a_day()))
    return valid_schedules


# --- USER INTERFACE CONTROL PANEL ---
file_names = [f"CE0{i}" for i in range(1, 10)] + ["CE10", "CE11"]

col1, col2 = st.columns(2)

with col1:
    target_code = st.selectbox("Select Target Schedule Code", file_names)
    max_days = st.slider("Maximum Days per Week", min_value=1, max_value=6, value=4)

with col2:
    preferred_gaps = st.number_input("Preferred Total Gap Periods", min_value=0, max_value=10, value=0)
    max_classes_per_day = st.slider("Max Classes Per Day", min_value=1, max_value=6, value=4)

excluded_input = st.text_input("Excluded Instructors (comma separated)", value="ALBASHIR")
excluded_drs = [x.strip() for x in excluded_input.split(",") if x.strip()]

# --- OPTIMIZATION & GRID RENDER ---
if st.button("🚀 Optimize Schedule", type="primary", use_container_width=True):
    try:
        results = optimize_schedule(
            target_code=target_code,
            file_names=file_names,
            max_days=max_days,
            preferred_gaps=preferred_gaps,
            max_classes_per_day=max_classes_per_day,
            excluded_instructors=excluded_drs
        )

        if not results:
            st.error("No valid schedules found matching these constraints.")
        else:
            st.success(f"Found {len(results)} valid schedules matching all criteria!")
            best = results[0]

            # Summary Bar
            st.markdown(
                f"**Days Occupied:** {len(best.days_occupied())} | "
                f"**Max Classes/Day:** {best.max_classes_in_a_day()} | "
                f"**Total Gaps:** {best.gaps()}"
            )

            # Palette of high-contrast background colors for subjects
            SUBJECT_COLORS = [
                "#1f4e78", "#1e6b39", "#8c2d19", "#542788", 
                "#7f6000", "#006064", "#4a148c", "#a239ea"
            ]

            # Map unique course codes to colors
            all_codes = sorted(list(set(
                s["code"] 
                for d in best.days.values() 
                for s in d.values() 
                if s is not None
            )))
            color_map = {code: SUBJECT_COLORS[i % len(SUBJECT_COLORS)] for i, code in enumerate(all_codes)}

            # Build grid data: Rows = Days, Columns = Period 1 to 6
            occupied_days = best.days_occupied()
            table_data = []

            for day in occupied_days:
                row = {"Day": day}
                for p in range(1, 7):
                    session = best.days[day][p]
                    if session:
                        code = session["code"]
                        name = session["name"]
                        t_type = session["type"][0].upper()
                        src = best.source_mapping.get(code, "N/A")
                        
                        # Full label containing code, subject name, type, and original source
                        row[f"Period {p}"] = f"{code}: {name} ({t_type})\n📍 From: {src}"
                    else:
                        row[f"Period {p}"] = "Free"
                table_data.append(row)

            df = pd.DataFrame(table_data).set_index("Day")

            # Pandas styling function
            def style_cells(val):
                if val == "Free":
                    return "color: #888888; text-align: center; font-style: italic;"
                for code, hex_color in color_map.items():
                    if val.startswith(code):
                        return (
                            f"background-color: {hex_color}; "
                            f"color: #ffffff; "
                            f"font-weight: 600; "
                            f"text-align: center; "
                            f"white-space: pre-wrap;"
                        )
                return "text-align: center; white-space: pre-wrap;"

            st.subheader("📅 Weekly Timetable Grid")
            
            # Apply map styling
            st.dataframe(
                df.style.map(style_cells),
                use_container_width=True,
                height=len(occupied_days) * 85 + 40
            )

    except Exception as e:
        st.error(f"Error running optimizer: {e}")
