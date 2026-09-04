import streamlit as st
import json
import os
import pandas as pd
from typing import List, Dict, Set, Tuple

# Page layout
st.set_page_config(page_title="Schedule Optimizer", page_icon="📅", layout="wide")
st.title("📅 University Schedule Optimizer")
st.write("Find the optimal conflict-free schedule tailored to your preferences.")

# --- Import/Define Classes & Functions from your script ---
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


# --- USER INTERFACE ---
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

            # Display Stats
            st.markdown(f"**Days Occupied:** {len(best.days_occupied())} | **Max Classes/Day:** {best.max_classes_in_a_day()} | **Total Gaps:** {best.gaps()}")

            # Build Clean Timetable Grid
            occupied_days = best.days_occupied()
            grid_dict = {}

            for p in range(1, 7):
                row = {}
                for day in occupied_days:
                    session = best.days[day][p]
                    if session:
                        row[day] = f"{session['code']} ({session['type'][0].upper()})"
                    else:
                        row[day] = "Free"
                grid_dict[f"Period {p}"] = row

            st.subheader("📅 Weekly Timetable Grid")
            st.dataframe(pd.DataFrame(grid_dict).T, use_container_width=True)

    except Exception as e:
        st.error(f"Error running optimizer: {e}")