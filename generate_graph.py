import pandas as pd
import matplotlib.pyplot as plt

# Load the result file
df = pd.read_csv('result.csv') # Make sure result.csv is in the same folder

# Create the bar chart
plt.figure(figsize=(10, 6))
plt.bar(df.iloc[:, 0], df['Topsis Score'], color='teal') # Assumes 1st col is Name
plt.xlabel('Alternatives')
plt.ylabel('Topsis Score')
plt.title('TOPSIS Ranking Results')
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Save the graph
plt.savefig('result_graph.png')
print("Graph saved as 'result_graph.png'")