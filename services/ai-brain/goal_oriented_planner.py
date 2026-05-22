import heapq
import logging

logger = logging.getLogger("GOAP-Planner")

class GOAPPlanner:
    """
    🧬 JKAI ZENITH: GOAP ENGINE v1.0 (A* Search)
    Tìm kiếm lộ trình tối ưu qua không gian trạng thái của kỹ năng.
    """
    def __init__(self, available_skills):
        self.skills = available_skills # List of skills with preconditions and effects

    def plan(self, start_state, goal_state):
        """
        Thực hiện giải thuật A* để tìm chuỗi hành động ngắn nhất.
        """
        # Node: (cost, current_state, path)
        open_list = []
        heapq.heappush(open_list, (0, start_state, []))
        
        closed_set = set()
        
        while open_list:
            cost, current_state, path = heapq.heappop(open_list)
            
            # Kiểm tra xem đã đạt mục tiêu chưa
            if self._is_goal_met(current_state, goal_state):
                return path
            
            state_key = frozenset(current_state.items())
            if state_key in closed_set:
                continue
            closed_set.add(state_key)
            
            # Duyệt qua các kỹ năng có thể thực hiện
            for skill in self.skills:
                if self._can_perform(skill, current_state):
                    new_state = self._apply_effect(skill, current_state)
                    new_path = path + [skill['name']]
                    new_cost = cost + skill.get('cost', 1)
                    
                    priority = new_cost + self._heuristic(new_state, goal_state)
                    heapq.heappush(open_list, (priority, new_state, new_path))
                    
        return None # Không tìm thấy đường đi

    def _is_goal_met(self, current, goal):
        return all(current.get(k) == v for k, v in goal.items())

    def _can_perform(self, skill, state):
        pre = skill.get('preconditions', {})
        return all(state.get(k) == v for k, v in pre.items())

    def _apply_effect(self, skill, state):
        new_state = state.copy()
        new_state.update(skill.get('effects', {}))
        return new_state

    def _heuristic(self, state, goal):
        # Đếm số lượng điều kiện mục tiêu chưa thỏa mãn
        return sum(1 for k, v in goal.items() if state.get(k) != v)

# Instance sẽ được nạp bởi Planner chính
