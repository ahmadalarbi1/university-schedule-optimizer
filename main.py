import json
import os
from typing import List, Dict, Set, Tuple

# Enable ANSI escape sequences in Windows CMD/PowerShell
os.system('')

class ColorPalette:
    """ANSI color codes for background and foreground styling."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Background colors with high-contrast text
    STYLES = [
        "\033[41;97m",   # Red background, White text
        "\033[42;30m",   # Green background, Black text
        "\033[43;30m",   # Yellow background, Black text
        "\033[44;97m",   # Blue background, White text
        "\033[45;97m",   # Magenta background, White text
        "\033[46;30m",   # Cyan background, Black text
        "\033[100;97m",  # Bright Black background, White text
        "\033[102;30m",  # Bright Green background, Black text
        "\033[104;97m",  # Bright Blue background, White text
        "\033[105;97m",  # Bright Magenta background, White text
    ]

    @classmethod
    def get_color_map(cls, course_codes: List[str]) -> Dict[str, str]:
        """Maps each unique course code to a unique ANSI color style."""
        color_map = {}
        for idx, code in enumerate(sorted(list(set(course_codes)))):
            color_map[code] = cls.STYLES[idx % len(cls.STYLES)]
        return color_map


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

    def print_schedule(self):
        """Prints a detailed colored schedule list with a color-coded legend."""
        all_codes = [
            s["code"] 
            for d in self.days.values() 
            for s in d.values() 
            if s is not None
        ]
        color_map = ColorPalette.get_color_map(all_codes)

        print("\n" + "=" * 60)
        print(f"{ColorPalette.BOLD} SCHEDULE: {self.class_code}{ColorPalette.RESET}")
        print(f" Days Occupied: {len(self.days_occupied())} | Max Classes/Day: {self.max_classes_in_a_day()} | Total Gaps: {self.gaps()}")
        print("=" * 60)
        
        # Color Legend
        print(f"\n{ColorPalette.BOLD}SUBJECT COLOR LEGEND:{ColorPalette.RESET}")
        unique_courses = {}
        for d in self.days.values():
            for s in d.values():
                if s and s["code"] not in unique_courses:
                    unique_courses[s["code"]] = s["name"]

        for code, name in sorted(unique_courses.items()):
            color = color_map[code]
            src = self.source_mapping.get(code, "N/A")
            print(f"  {color} {code} {ColorPalette.RESET} {name} (Borrowed from: {src})")
        
        print("-" * 60)

        # Print Day by Day
        for day in self.DAYS:
            if day not in self.days_occupied():
                continue
            print(f"\n{ColorPalette.BOLD}{day}:{ColorPalette.RESET}")
            for period, session in self.days[day].items():
                if session:
                    color = color_map[session["code"]]
                    badge = f"{color} {session['code']} ({session['type']}) {ColorPalette.RESET}"
                    print(f"  Period {period}: {badge} - {session['name']} (Dr. {session['instructor']})")
                else:
                    print(f"  Period {period}: \033[90mFree\033[0m")

    def print_grid(self):
        """Prints the schedule in a compact, colored weekly timetable grid."""
        all_codes = [
            s["code"] 
            for d in self.days.values() 
            for s in d.values() 
            if s is not None
        ]
        color_map = ColorPalette.get_color_map(all_codes)
        occupied_days = self.days_occupied()

        print("\n" + "=" * 80)
        print(f"{ColorPalette.BOLD}WEEKLY TIMETABLE GRID ({self.class_code}){ColorPalette.RESET}")
        print("=" * 80)

        # Header Row
        header = f"{'Period':<8} | " + " | ".join([f"{day:<14}" for day in occupied_days])
        print(ColorPalette.BOLD + header + ColorPalette.RESET)
        print("-" * len(header))

        # Rows for Periods 1 to 6
        for p in range(1, 7):
            row_cells = []
            for day in occupied_days:
                session = self.days[day][p]
                if session:
                    color = color_map[session["code"]]
                    t_abbr = session['type'][0].upper()
                    label = f"{session['code']} ({t_abbr})"
                    cell = f"{color}{label:^14}{ColorPalette.RESET}"
                else:
                    cell = f"\033[90m{'---':^14}\033[0m"
                row_cells.append(cell)

            print(f"Period {p:<2} | " + " | ".join(row_cells))

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
        return {
            day: sum(1 for s in periods.values() if s is not None)
            for day, periods in self.days.items()
        }

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
            # Safely handle None values for instructor names
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
            
            sch = Schedule(all_sessions, "Optimized_Combination", source_mapping=source_map)
            valid_schedules.append(sch)
            return

        current_course = required_courses[course_index]

        for bundle in catalog[current_course]:
            if occupied_slots.isdisjoint(bundle.slots):
                new_slots = occupied_slots | bundle.slots
                
                day_counts: Dict[str, int] = {}
                for day, _ in new_slots:
                    day_counts[day] = day_counts.get(day, 0) + 1
                
                if len(day_counts) <= max_days and max(day_counts.values(), default=0) <= max_classes_per_day:
                    backtrack(
                        course_index + 1,
                        current_bundles + [bundle],
                        new_slots
                    )

    backtrack(0, [], set())

    valid_schedules.sort(
        key=lambda s: (
            len(s.days_occupied()), 
            abs(s.gaps() - preferred_gaps),
            s.max_classes_in_a_day()
        )
    )

    return valid_schedules


if __name__ == "__main__":
    file_names = [f"CE0{i}" for i in range(1, 10)] + ["CE10", "CE11"]
    
    # Pass instructor names (or partial names, case-insensitive) to exclude:
    excluded_drs = ["ALBASHIR"]
    print(file_names)
    target_code = input("Enter target schedule code: ")
    max_days = int(input("Enter Maximum days: "))
    preferred_gaps = int(input("Enter prefered gaps: "))
    max_classes_per_day = int(input("Enter maximum number of classes per day: "))

    optimized_results = optimize_schedule(
        target_code, 
        file_names=file_names, 
        max_days = max_days, 
        preferred_gaps = preferred_gaps,
        max_classes_per_day = max_classes_per_day,
        excluded_instructors=excluded_drs
    )
    
    print(f"Found {len(optimized_results)} valid schedules matching all constraints!")

    if optimized_results:
        best = optimized_results[0]
        best.print_schedule()
        best.print_grid()
