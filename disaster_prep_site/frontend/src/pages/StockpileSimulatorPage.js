import React, { useState } from 'react';
import StockpileInputForm from '../components/StockpileInputForm';
import StockpileResultsTable from '../components/StockpileResultsTable';
import './StockpileSimulatorPage.css'; // Page-specific styling

function StockpileSimulatorPage() {
  const initialFamilyMembers = {
    adult: 0,
    child_teen: 0, // "子供(中学生以上)"
    child_younger: 0, // "子供"
    infant: 0,
    elderly: 0,
  };
  const [familyMembers, setFamilyMembers] = useState(initialFamilyMembers);
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleInputChange = (category, value) => {
    const count = parseInt(value, 10);
    setFamilyMembers(prev => ({
      ...prev,
      [category]: count >= 0 ? count : 0,
    }));
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    setError(null);
    setResults(null); // Clear previous results

    // Map frontend categories to backend categories
    // Summing child_teen and child_younger into 'child'
    const payload = {
      family_members: {
        adult: familyMembers.adult,
        child: familyMembers.child_teen + familyMembers.child_younger,
        infant: familyMembers.infant,
        elderly: familyMembers.elderly,
      },
    };

    // Filter out categories with 0 members to avoid sending them
    for (const key in payload.family_members) {
        if (payload.family_members[key] === 0) {
            delete payload.family_members[key];
        }
    }
    // If all categories are 0, send an empty object or handle as needed
    // The backend currently handles empty family_members by returning empty results, which is fine.

    try {
      // Using relative path due to proxy in package.json
      const response = await fetch('/api/stockpile_simulator', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let errData;
        try {
            errData = await response.json();
        } catch (e) {
            // If response is not JSON, use status text
            throw new Error(response.statusText || `HTTP error! status: ${response.status}`);
        }
        throw new Error(errData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="stockpile-simulator-page">
      <h1>防災備蓄シミュレータ</h1>
      <p>各世代の人数を入力して「計算する」ボタンを押してください。<br/>最低限必要な3日分の備蓄量と、推奨される7日分の備蓄量を計算します。</p>
      <StockpileInputForm
        familyMembers={familyMembers}
        onInputChange={handleInputChange}
        onSubmit={handleSubmit}
        isLoading={isLoading}
      />
      {isLoading && <p className="loading-message">計算中...</p>}
      {error && <p className="error-message">エラー: {error}</p>}
      {results && <StockpileResultsTable results={results} />}
    </div>
  );
}

export default StockpileSimulatorPage;
