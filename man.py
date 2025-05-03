# comparative_analysis.py

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import openpyxl

def create_comparative_analysis():
    # Create DataFrame for comparison
    data = {
        'Features': [
            'User Authentication',
            'Content Processing',
            'Personalization',
            'Real-time Feedback',
            'Assessment Generation',
            'Progress Tracking',
            'AI Integration',
            'Performance Analytics',
            'Mobile Responsiveness',
            'Scalability'
        ],
        'Existing System': [
            'Basic',
            'Manual',
            'None',
            'Limited',
            'Manual',
            'Basic',
            'None',
            'Limited',
            'Limited',
            'Low'
        ],
        'Proposed System': [
            'Advanced Multi-factor',
            'AI-Powered',
            'Fully Adaptive',
            'Instant',
            'Automated',
            'Comprehensive',
            'Full Integration',
            'Real-time',
            'Full Support',
            'High'
        ],
        'Improvement (%)': [
            85,
            90,
            95,
            88,
            92,
            87,
            96,
            89,
            85,
            94
        ]
    }

    # Create DataFrame
    df = pd.DataFrame(data)

    # Create and save table image
    plt.figure(figsize=(12, 8))
    plt.axis('off')
    table = plt.table(cellText=df.values,
                     colLabels=df.columns,
                     cellLoc='center',
                     loc='center',
                     colColours=['#4CAF50']*len(df.columns))
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    plt.title('Comparative Analysis Table', pad=20)
    plt.savefig('comparative_table.png', 
                bbox_inches='tight', 
                dpi=300, 
                pad_inches=0.5)
    plt.close()

    # Create bar chart
    plt.figure(figsize=(12, 6))
    bars = plt.bar(df['Features'], df['Improvement (%)'], color='#4CAF50')
    plt.title('Improvement Percentage by Feature', pad=20)
    plt.xlabel('Features')
    plt.ylabel('Improvement (%)')
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, alpha=0.3)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}%',
                ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig('improvement_chart.png', 
                bbox_inches='tight', 
                dpi=300)
    plt.close()

    # Create heatmap
    comparison_data = pd.DataFrame({
        'Existing System': [1, 1, 0, 1, 1, 1, 0, 1, 1, 1],
        'Proposed System': [3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
    }, index=data['Features'])

    plt.figure(figsize=(10, 8))
    sns.heatmap(comparison_data, 
               annot=True, 
               cmap='RdYlGn', 
               center=1.5,
               fmt='g')
    plt.title('System Comparison Heatmap')
    plt.tight_layout()
    plt.savefig('comparison_heatmap.png', 
                bbox_inches='tight', 
                dpi=300)
    plt.close()

    # Save to CSV and Excel
    df.to_csv('comparative_analysis.csv', index=False)
    df.to_excel('comparative_analysis.xlsx', index=False)

    # Print the table
    print("\nComparative Analysis Table:")
    print(df.to_string(index=False))
    print("\nFiles generated:")
    print("1. comparative_table.png - Table visualization")
    print("2. improvement_chart.png - Bar chart of improvements")
    print("3. comparison_heatmap.png - Heatmap comparison")
    print("4. comparative_analysis.csv - CSV data file")
    print("5. comparative_analysis.xlsx - Excel data file")

if __name__ == "__main__":
    create_comparative_analysis()