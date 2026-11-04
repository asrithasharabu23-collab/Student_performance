import pandas as pd

# Read CSV file
data = pd.read_csv("students.csv")

# Display first five rows
print("FIRST FIVE STUDENTS")
print(data.head())

# Display number of rows and columns
print("\nDATASET SHAPE")
print(data.shape)

# Display column names
print("\nCOLUMN NAMES")
print(data.columns)

# Display dataset information
print("\nDATASET INFORMATION")
print(data.info())

# Display statistical details
print("\nSTATISTICAL INFORMATION")
print(data.describe())

# Check missing values
print("\nMISSING VALUES")
print(data.isnull().sum())