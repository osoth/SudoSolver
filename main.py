import time
import cv2
import re
import pytesseract
import os
from selenium.webdriver import ActionChains
from tqdm import tqdm
import numpy as np
import multiprocessing

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

M = 9


def delete():
	try:
		os.remove("current_board.png")
	except Exception as e:
		print("Error while deleting current_board.png:", e)

	# delete all cells/cell_{i}_{j}.png in range(9)
	for i in range(9):
		for j in range(9):
			try:
				os.remove(f"cells/cell_{i}_{j}.png")
			except Exception as e:
				print(f"Error while deleting cell_{i}_{j}.png:", e)


def solve(grid, row, col, num):
	for x in range(9):
		if grid[row][x] == num:
			return False

	for x in range(9):
		if grid[x][col] == num:
			return False

	startRow = row - row % 3
	startCol = col - col % 3
	for i in range(3):
		for j in range(3):
			if grid[i + startRow][j + startCol] == num:
				return False
	return True


def Suduko(grid, row, col):
	if (row == M - 1 and col == M):
		return True
	if col == M:
		row += 1
		col = 0
	if grid[row][col] > 0:
		return Suduko(grid, row, col + 1)
	for num in range(1, M + 1, 1):

		if solve(grid, row, col, num):

			grid[row][col] = num
			if Suduko(grid, row, col + 1):
				return True
		grid[row][col] = 0
	return False


def detect_numbers(image):
	img = cv2.imread(image)
	rgb = img

	# Perform thresholding or other preprocessing if needed
	# For example:
	# _, threshold_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	# Perform OCR
	text = pytesseract.image_to_string(rgb, config="--psm 13")
	text = text.replace("\n", "")
	text = re.findall(r'\d+', text)
	text = text[0] if text else None
	if text is None:
		text = text = pytesseract.image_to_string(rgb, config="--psm 10")
		text = text.replace("\n", "")
		text = re.findall(r'\d+', text)
		text = text[0] if text else None
	# if part of the text is a number return the number else return None
	if text is not None:
		if text == "38":
			return 8
		else:
			return int(text)
	else:
		return None


def print_board(board):
	print("-" * 54)
	for i in range(9):
		print("|", end="")
		for j in range(9):
			if board[i][j] == None:
				print("     ", end="|")
			else:
				print(f"  {board[i][j]}  ", end="|")
		print("\n" + "-" * 54)


def process_image(i, j):
	x_start = x_coords[i] + 5
	x_end = x_coords[i + 1] - 5
	y_start = y_coords[j] + 5
	y_end = y_coords[j + 1] - 5
	cell_image = cropped_image[y_start:y_end, x_start:x_end]
	cell_image = cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY)
	_, threshold_image = cv2.threshold(cell_image, 128, 255, cv2.THRESH_BINARY)
	kernel = np.ones((3, 3), np.float32) / 50
	end_image = cv2.filter2D(threshold_image, -1, kernel)
	# Define the old color and the new color
	old_value = 32

	# Find pixels with the exact old value and replace them with 255 (white)
	mask = end_image >= old_value - 15
	end_image[mask] = 255
	end_image = cv2.GaussianBlur(end_image, (5, 5), 0)

	# Save the modified image
	cv2.imwrite(f'cells/cell_{j}_{i}.png', end_image)


if __name__ == "__main__":
	options = webdriver.ChromeOptions()
	options.add_extension('/home/whoami/Documents/ChromeExtensions/uBlock Origin 1.55.0.0.crx')
	driver = webdriver.Chrome(options=options)
	driver.maximize_window()
	driver.get("https://sudoku.com/de/evil/")
	try:
		time.sleep(1)
		# Find the accept button within the cookie button group
		accept_cookies_button = driver.find_element(By.ID, "onetrust-accept-btn-handler")
		# Click on the accept cookies button
		accept_cookies_button.click()
	except Exception as e:
		print("Error while accepting cookies:", e)
	# use the keyboard library to press ctrl and + to zoom in
	driver.execute_script("document.body.style.zoom='200%'")
	driver.execute_script("window.scrollBy(0, 250);")
	print("Still there")
	time.sleep(5)
	driver.save_screenshot("current_board.png")
	print("Screenshot saved")
	image = cv2.imread('current_board.png')
	# Define the coordinates of the rectangle to crop
	x1, y1 = 23, 29
	x2, y2 = 833, 839

	# Crop the image
	cropped_image = image[y1:y2, x1:x2]

	# Overwrite the old file with the cropped image
	cv2.imwrite('current_board.png', cropped_image)

	cropped_image = cv2.imread('current_board.png')

	# Define the coordinates for cutting the image
	x_coords = [0, 90, 180, 270, 360, 450, 540, 630, 720, 810]
	y_coords = [0, 90, 180, 270, 360, 450, 540, 630, 720, 810]

	# Iterate over the coordinates and crop the image into parts
	num_processes = 4

	# Create a Pool of processes
	with multiprocessing.Pool(processes=num_processes) as pool:
		# Map the process_image function to each combination of i and j
		pool.starmap(process_image, [(i, j) for i in range(9) for j in range(9)])

	board = [[0 for i in range(9)] for j in range(9)]

	for i in tqdm(range(9)):
		for j in range(9):
			a = detect_numbers(f"cells/cell_{i}_{j}.png")
			# if a is integer board[i][j] = int(a)
			if a is not None:
				board[i][j] = a
			else:
				board[i][j] = 0
	board_copy = board
	# replace all 0s with None
	board_copy = [[None if x == 0 else x for x in y] for y in board_copy]
	print_board(board_copy)
	if Suduko(board, 0, 0):
		print_board(board)
	else:
		print("No solution exists")

	for i in range(9):
		for j in range(9):
			if j != 8:
				ActionChains(driver).send_keys(str(board[i][j])).perform()
				ActionChains(driver).send_keys(Keys.ARROW_RIGHT).perform()
			else:
				ActionChains(driver).send_keys(str(board[i][j])).perform()
				ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
				for z in range(8):
					ActionChains(driver).send_keys(Keys.ARROW_LEFT).perform()

	a = input()
	while a != "q":
		a = input()
	if a == "q":
		driver.quit()
		delete()
		print("Bye Bye!")

