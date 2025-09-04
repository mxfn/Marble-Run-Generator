
import random

xSize = 5
ySize = 5
# matrix = [[0 for _ in range(xSize)] for _ in range(ySize)]
matrix = None
num_moves = 0
start_cell = (2, ySize-1) # (x, y)

# Directions: up, down, left, right
directions = [(-1,0), (1,0), (0,-1), (0,1)]

# 0:+X, 1:+Y, 2:-X, 3:-Y
# 4:+Y+X, 5:-X+Y, 6:-Y-X, 7:+X-Y
# 8:+Y-X, 9:-X-Y, 10:-Y+X, 11:+X+Y
# 0:[0,0], 1:[1,1], 2:[2,2], 3:[3,3]
# 4:[1,0], 5:[2,1], 6:[3,2], 7:[0,3]
# 8:[1,2], 9:[2,3], 10:[3,0], 11:[0,1]
track_type_dict = {(0,0): 0, (1,1): 1, (2,2): 2, (3,3): 3, (1,0): 4, (2,1): 5, (3,2): 6, (0,3): 7, (1,2): 8, (2,3): 9, (3,0): 10, (0,1): 11}

def create_matrix(x_size, y_size):
    global xSize
    global ySize
    global matrix
    xSize = x_size
    ySize = y_size
    matrix = [[0 for _ in range(xSize)] for _ in range(ySize)]
    matrix[ySize-2][0] = x_size*y_size-3
    matrix[ySize-2][1] = x_size*y_size-2
    matrix[ySize-1][0] = x_size*y_size
    matrix[ySize-1][1] = x_size*y_size-1
    return matrix

def is_valid(x, y):
    return 0 <= x < xSize and 0 <= y < ySize and matrix[y][x] == 0

def is_valid2(x, y, num):
    # If both spots are 0, return true
    # If you're at one of the two spots and the other spot is not zero, then the spot you're at must be xSize*ySize-5
    if (x, y) == (0, ySize-4) or (x, y) == (1, ySize-3):
        if matrix[ySize-4][0] == 0 and matrix[ySize-3][1] == 0:
            return True
        elif num != xSize*ySize-5:
            print("num: ", num)
            return False
    # if (x, y) == (0, ySize-4):
    #     if num != xSize*ySize-5 and matrix[ySize-3][1] != xSize*ySize-5:
    #         return False
    # if (x, y) == (1, ySize-3):
    #     if num != xSize*ySize-5 and matrix[ySize-4][0] != xSize*ySize-5:
    #         return False
    return True

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

# The only place where a dead end is valid is at the last cell
def has_invalid_dead_end(x, y):
    # A space is a dead end if it only has one valid neighbor and it isn't occupied by the next move
    end_cell = [0, ySize-3] # this is the only cell where a dead end is acceptable
    empty_cells = [[x, y] for y in range(len(matrix)) for x in range(len(matrix[y])) if matrix[y][x] == 0]
    for cell in empty_cells:
        cell_x = cell[0]
        cell_y = cell[1]
        is_up_free = is_valid(cell_x, cell_y - 1)
        is_down_free = is_valid(cell_x, cell_y + 1)
        is_left_free = is_valid(cell_x - 1, cell_y)
        is_right_free = is_valid(cell_x + 1, cell_y)
        if is_up_free + is_down_free + is_left_free + is_right_free == 1 and cell != [x, y] and cell != end_cell:
            return True
    return False

# the only condition that is necessary is the is_valid condition, but the others significantly speed up the path generation by ignoring infeasible paths
def accept_neighbor(x, y, num):
    valid = True
    if not is_valid(x, y):
        valid = False
    if is_subdividing_space(x, y):
        valid = False
    # if num_dead_ends(x, y) > 1:
    #     valid = False
    if has_invalid_dead_end(x, y):
        valid = False
    if not is_valid2(x, y, num):
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
    if num == xSize * ySize - 4:
        return True
    neighbors = [(x+dx, y+dy) for dx, dy in directions if accept_neighbor(x+dx, y+dy, num+1)]
    # Warnsdorff's heuristic: sort by number of onward moves (ascending)
    # Also add some randomness to the sorting
    neighbors.sort(key=lambda pos: onward_moves_randomized(*pos, 0.8))
    for nx, ny in neighbors:
        if fill_path(nx, ny, num + 1):
            return True
    matrix[y][x] = 0  # Backtrack
    return False

def generate_path(x_size, y_size):
    # global matrix
    global num_moves
    create_matrix(x_size, y_size)
    while True:
        # matrix = [[0 for _ in range(xSize)] for _ in range(ySize)]
        num_moves = 0
        if fill_path(start_cell[0], start_cell[1], 1):
            break
    return matrix

def is_within_bounds(row, col):
    return 0 <= col < xSize and 0 <= row < ySize

def find_prev_cell(current_cell):
    row = current_cell[0]
    col = current_cell[1]
    cell_val = matrix[row][col]
    cell_search_val = cell_val-1
    directions = [(0,-1), (1,0), (0,1), (-1,0)]
    for i in range(len(directions)):
        test_row = row+directions[i][0]
        test_col = col+directions[i][1]
        if (is_within_bounds(test_row, test_col)):
            test_cell_val = matrix[test_row][test_col]
            if test_cell_val == cell_search_val:
                direction = i
                return direction
    return None

def find_next_cell(current_cell):
    row = current_cell[0]
    col = current_cell[1]
    cell_val = matrix[row][col]
    cell_search_val = cell_val+1
    directions = [(0,1), (-1,0), (0,-1), (1,0)]
    for i in range(len(directions)):
        test_row = row+directions[i][0]
        test_col = col+directions[i][1]
        if (is_within_bounds(test_row, test_col)):
            test_cell_val = matrix[test_row][test_col]
            if test_cell_val == cell_search_val:
                direction = i
                return direction
    return None

# Create a matrix showing what type of track should be used
def generate_type_matrix():
    type_matrix = [[0 for _ in range(len(matrix[0]))] for _ in range(len(matrix))]
    for row in range(len(type_matrix)):
        for col in range(len(type_matrix[0])):
            cell_val = matrix[row][col]
            prev_cell_dir = 0
            next_cell_dir = 0
            if cell_val > 1:
                prev_cell_dir = find_prev_cell([row, col])
            if cell_val < len(type_matrix)*len(type_matrix[0]):
                next_cell_dir = find_next_cell([row, col])
            if cell_val == 1:
                prev_cell_dir = next_cell_dir
            if cell_val == len(type_matrix)*len(type_matrix[0]):
                next_cell_dir = prev_cell_dir
            track_type_key = (prev_cell_dir, next_cell_dir)
            type_matrix[row][col] = track_type_dict[track_type_key]
    return type_matrix

the_matrix = generate_path(xSize, ySize)
type_matrix = generate_type_matrix()


width = len(str(xSize * ySize))
print()
for row in the_matrix:
    print(' '.join(f"{cell:>{width}}" for cell in row))
print()
for row in type_matrix:
    print(' '.join(f"{cell:>{width}}" for cell in row))