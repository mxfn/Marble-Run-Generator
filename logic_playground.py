
import random

xSize = 15
ySize = 15
matrix = [[0 for _ in range(xSize)] for _ in range(ySize)]
num_moves = 0

# Directions: up, down, left, right
directions = [(-1,0), (1,0), (0,-1), (0,1)]

def is_valid(x, y):
    return 0 <= x < xSize and 0 <= y < ySize and matrix[y][x] == 0


def onward_moves_randomized(x, y, probability=0.8):
    def randomizer(probability):
        return 1 if random.random() < probability else 0
    return sum(is_valid(x+dx, y+dy)*randomizer(probability) for dx, dy in directions)


# If the next move subdivides the empty space into two separate spaces, then the next move should be invalid
def is_subdividing_space(x, y):
    matrix_copy = [row[:] for row in matrix]  # Create a copy of the matrix
    if is_valid(x, y):
        matrix_copy[y][x] = 1
    rows, cols = len(matrix_copy), len(matrix_copy[0])
    visited = [[False] * cols for _ in range(rows)]

    def dfs(r, c):
        if (
            r < 0 or r >= rows or
            c < 0 or c >= cols or
            matrix_copy[r][c] != 0 or
            visited[r][c]
        ):
            return
        visited[r][c] = True
        # Explore all 4 directions (up, down, left, right)
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)

    zero_groups = 0
    for r in range(rows):
        for c in range(cols):
            if matrix_copy[r][c] == 0 and not visited[r][c]:
                zero_groups += 1
                if zero_groups > 1:
                    return True
                dfs(r, c)

    return False

# Count the number of dead ends. The grid can only have one dead end. You can make this more powerful by checking if you will be stuck between constrictions
def num_dead_ends(x, y):
    # A space is a dead end if it only has one valid neighbor and it isn't occupied by the next move
    num_dead_ends = 0
    empty_cells = [[x, y] for y in range(len(matrix)) for x in range(len(matrix[y])) if matrix[y][x] == 0]
    for cell in empty_cells:
        cell_x = cell[0]
        cell_y = cell[1]
        is_up_free = is_valid(cell_x, cell_y - 1)
        is_down_free = is_valid(cell_x, cell_y + 1)
        is_left_free = is_valid(cell_x - 1, cell_y)
        is_right_free = is_valid(cell_x + 1, cell_y)
        if is_up_free + is_down_free + is_left_free + is_right_free == 1 and cell != [x, y]:
            num_dead_ends += 1
    return num_dead_ends

# the only condition that is necessary is the is_valid condition, but the others significantly speed up the path generation by ignoring infeasible paths
def accept_neighbor(x, y):
    valid = True
    if not is_valid(x, y):
        valid = False
    if is_subdividing_space(x, y):
        valid = False
    if num_dead_ends(x, y) > 1:
        valid = False
    return valid

def fill_path(x, y, num):
    global num_moves
    num_moves += 1
    print("num_moves: ", num_moves)
    if (num_moves%10) == 0:
        width = len(str(xSize * ySize))
        for row in matrix:
            print(' '.join(f"{cell:>{width}}" for cell in row))
    if num_moves > 2000: # If the program is struggling with the current path, force the program to generate a new path from scratch
        return False
    
    matrix[y][x] = num
    if num == xSize * ySize:
        return True
    neighbors = [(x+dx, y+dy) for dx, dy in directions if accept_neighbor(x+dx, y+dy)]
    # Warnsdorff's heuristic: sort by number of onward moves (ascending)
    # Also add some randomness to the sorting
    neighbors.sort(key=lambda pos: onward_moves_randomized(*pos, 0.8))
    for nx, ny in neighbors:
        if fill_path(nx, ny, num + 1):
            return True
    matrix[y][x] = 0  # Backtrack
    return False

# Try until a full path is found
num_tries = 0
while True:
    matrix = [[0 for _ in range(xSize)] for _ in range(ySize)]
    num_moves = 0
    if fill_path(0, 0, 1):
        break

# Print the matrix with evenly spaced numbers
width = len(str(xSize * ySize))
for row in matrix:
    print(' '.join(f"{cell:>{width}}" for cell in row))