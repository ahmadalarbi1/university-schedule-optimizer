import json

class Schedule:
    DAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

    def __init__(self, schedule_data: list,class_code : str):
        # Initialize a nested dict: { "Saturday": {1: None, 2: None, ...}, ... }
        self.days = {day: {p: None for p in range(1, 7)} for day in self.DAYS}
        self.class_code = class_code
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
        for day, periods in self.days.items():
            print(f"\n{day}:")
            for period, session in periods.items():
                if session:
                    print(f"  Period {period}: {session['name']}, {session['type']}")
                else:
                    print(f"  Period {period}: Free")

    def gaps (self):
        gaps_count = 0
        for day in self.days:
            temp = 0
            for i in range(1, 6):
                if self.days[day][i] is not None:
                    for i in range(i+1, 6):
                        if self.days[day][i] is None:
                            temp += 1
                        else:
                            gaps_count += temp
                            break
        return gaps_count

    def days_occupied (self):
        days_occ = []
        empty_day = {i:None for i in range(1,7)}
        for day in self.days:
            if self.days[day] != empty_day:
                days_occ.append(day)
        return days_occ

def least_gaps (schedules : list) -> str:
    best_gaps = 100
    for schedule in schedules:
        if schedule.gaps() < best_gaps:
            best_gaps = schedule.gaps()
            best_schedule = schedule
    return best_schedule.class_code

def least_days_occupied (schedules : list) -> str:
    least_days = 10
    for schedule in schedules:
        if len(schedule.days_occupied()) < least_days:
            least_days = len(schedule.days_occupied())
            least_schedule = schedule
    return least_schedule.class_code

if __name__ == "__main__":
    file_names = []
    schedules = []
    for i in range(1,10):
        file_names.append(f"CE0{i}")
    file_names.append("CE10")
    file_names.append("CE11")
    for sch in file_names:
        with open(f"{sch}.json", encoding="utf-8") as file:
            temp = json.load(file)
            schedules.append(Schedule(temp,f"{sch}"))

    for s in schedules:
        print(f"{s.class_code}, gaps: {s.gaps()}")

    print()
    for s in schedules:
        print(f"{s.class_code}, days: {len(s.days_occupied())}")
    print(least_gaps(schedules))
    print(least_days_occupied(schedules))
