import React from 'react';
import './StockpileResultsTable.css'; 

function StockpileResultsTable({ results }) {
  if (!results || results.length === 0) {
    return <p className="no-results">計算結果はありません。</p>;
  }

  // Group results by category
  const groupedResults = results.reduce((acc, item) => {
    const category = item.category || "その他";
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(item);
    return acc;
  }, {});

  return (
    <div className="results-table-container">
      {Object.entries(groupedResults).map(([category, items]) => (
        <div key={category} className="category-section">
          <h3 className="category-title">{category}</h3>
          <table className="stockpile-results-table">
            <thead>
              <tr>
                <th>備蓄品名</th>
                <th>最低限 (3日分)</th>
                <th>安心 (7日分)</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>{item.minimum_quantity} {item.unit}</td>
                  <td>{item.recommended_quantity} {item.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

export default StockpileResultsTable;
