import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [diseaseName, setDiseaseName] = useState('');
  const [maxResults, setMaxResults] = useState(10);
  const [minScore, setMinScore] = useState(0.2);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [validatingIndex, setValidatingIndex] = useState(null);
  const [clinicalResults, setClinicalResults] = useState({});

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);
    setClinicalResults({});
    setLoadingMessage('🔍 Searching for disease in database...');

    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          disease_name: diseaseName,
          min_score: minScore,
          max_results: maxResults,
        }),
      });

      const data = await response.json();

      if (!data.success) {
        setError({
          message: data.error || 'An error occurred',
          suggestion: data.suggestion || 'Please try again with a different disease name.'
        });
        setLoadingMessage('');
        setLoading(false);
        return;
      }

      setResults(data);
      setLoadingMessage('');
      
    } catch (err) {
      console.error('Error:', err);
      setError({
        message: 'Failed to connect to server',
        suggestion: 'Please make sure the backend server is running on port 8000.'
      });
      setLoadingMessage('');
    } finally {
      setLoading(false);
    }
  };

  const handleClinicalValidation = async (candidate, index) => {
    setValidatingIndex(index);
    
    try {
      const response = await fetch('http://localhost:8000/validate_clinical', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          drug_name: candidate.drug_name,
          disease_name: results.disease.name,
          drug_data: {
            mechanism: candidate.mechanism,
            indication: candidate.indication
          },
          disease_data: {
            name: results.disease.name,
            description: results.disease.description
          }
        }),
      });

      const data = await response.json();

      if (data.success) {
        setClinicalResults(prev => ({
          ...prev,
          [index]: data.validation
        }));
      } else {
        setClinicalResults(prev => ({
          ...prev,
          [index]: {
            error: data.error || 'Validation failed'
          }
        }));
      }
    } catch (err) {
      console.error('Clinical validation error:', err);
      setClinicalResults(prev => ({
        ...prev,
        [index]: {
          error: 'Failed to connect to validation service'
        }
      }));
    } finally {
      setValidatingIndex(null);
    }
  };

  const getRiskColor = (riskLevel) => {
    switch(riskLevel) {
      case 'LOW': return '#10b981';
      case 'MEDIUM': return '#f59e0b';
      case 'HIGH': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.7) return '#10b981';
    if (score >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  const getConfidenceBadge = (confidence) => {
    const colors = {
      high: 'bg-green-500 text-white',
      medium: 'bg-yellow-500 text-white',
      low: 'bg-red-500 text-white',
    };
    return colors[confidence?.toLowerCase()] || colors.low;
  };

  useEffect(() => {
    if (results) {
      const molecules = document.querySelectorAll('.molecule-3d');
      molecules.forEach((mol, i) => {
        mol.style.animation = `rotate3d ${3 + i * 0.5}s linear infinite`;
      });
    }
  }, [results]);

  return (
    <div className="min-h-screen bg-black relative overflow-hidden">
      {/* Graph paper background */}
      <div className="fixed inset-0 opacity-20 pointer-events-none">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(0, 255, 0, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 0, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px'
        }}></div>
      </div>

      {/* Animated grid lines */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="grid-line-h"></div>
        <div className="grid-line-v"></div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-7xl relative z-10">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-6xl font-black mb-4 text-green-400 glitch-text" data-text="DRUG REPURPOSING ENGINE">
            🧬 DRUG REPURPOSING ENGINE
          </h1>
          <p className="text-green-300 text-xl font-mono">
            {'>'} AI-POWERED THERAPEUTIC DISCOVERY SYSTEM {'<'}
          </p>
          <div className="mt-4 flex justify-center gap-4">
            <div className="status-indicator">
              <span className="status-dot"></span>
              <span className="text-green-400 text-sm font-mono">DATABASES: ONLINE</span>
            </div>
            <div className="status-indicator">
              <span className="status-dot"></span>
              <span className="text-green-400 text-sm font-mono">AI: ACTIVE</span>
            </div>
          </div>
        </div>

        {/* Input Form */}
        <div className="terminal-window mb-8">
          <div className="terminal-header">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
            </div>
            <div className="text-green-400 font-mono text-sm">
              QUERY_INTERFACE.EXE
            </div>
          </div>
          
          <div className="terminal-body">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-green-400 font-mono mb-2 text-sm">
                  {'>'} TARGET_DISEASE:
                </label>
                <input
                  type="text"
                  value={diseaseName}
                  onChange={(e) => setDiseaseName(e.target.value)}
                  placeholder="Enter disease name (e.g., Parkinson Disease)..."
                  className="terminal-input"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-green-400 font-mono mb-2 text-sm">
                    {'>'} MAX_CANDIDATES:
                  </label>
                  <input
                    type="number"
                    value={maxResults}
                    onChange={(e) => setMaxResults(Number(e.target.value))}
                    min="1"
                    max="50"
                    className="terminal-input"
                  />
                </div>

                <div>
                  <label className="block text-green-400 font-mono mb-2 text-sm">
                    {'>'} MIN_SCORE_THRESHOLD:
                  </label>
                  <input
                    type="number"
                    value={minScore}
                    onChange={(e) => setMinScore(Number(e.target.value))}
                    min="0"
                    max="1"
                    step="0.1"
                    className="terminal-input"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="terminal-button"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="loader"></span>
                    ANALYZING...
                  </span>
                ) : (
                  '⚡ INITIATE REPURPOSING ANALYSIS'
                )}
              </button>
            </form>

            {loadingMessage && (
              <div className="mt-6 p-4 border-2 border-green-500 bg-black bg-opacity-50">
                <p className="text-green-400 font-mono text-sm flex items-center gap-2">
                  <span className="loader-small"></span>
                  {loadingMessage}
                </p>
              </div>
            )}

            {error && (
              <div className="mt-6 p-4 border-2 border-red-500 bg-black bg-opacity-50">
                <p className="text-red-400 font-mono text-sm font-bold mb-2">
                  ❌ ERROR: {error.message}
                </p>
                <p className="text-yellow-400 font-mono text-xs">
                  💡 SUGGESTION: {error.suggestion}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Results */}
        {results && results.success && (
          <div className="space-y-8">
            {/* Disease Info */}
            <div className="terminal-window">
              <div className="terminal-header">
                <div className="text-green-400 font-mono text-sm">
                  DISEASE_ANALYSIS.DAT
                </div>
              </div>
              
              <div className="terminal-body">
                <h2 className="text-4xl font-black text-green-400 mb-6 font-mono glitch-text" data-text={results.disease?.name}>
                  {results.disease?.name || diseaseName}
                </h2>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                  <div className="stat-card">
                    <div className="stat-label">GENES_IDENTIFIED</div>
                    <div className="stat-value">{results.disease?.genes_count || 0}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">PATHWAYS_MAPPED</div>
                    <div className="stat-value">{results.disease?.pathways_count || 0}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">CANDIDATES_FOUND</div>
                    <div className="stat-value">{results.candidates?.length || 0}</div>
                  </div>
                </div>

                {results.disease?.top_genes && results.disease.top_genes.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-green-400 font-mono mb-3 text-sm">
                      {'>'} TARGET_GENES:
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {results.disease.top_genes.map((gene) => (
                        <span key={gene} className="gene-badge">
                          {gene}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Filtered Out Drugs Section */}
            {results.filtered_count > 0 && (
              <div className="terminal-window">
                <div className="terminal-header">
                  <div className="text-red-400 font-mono text-sm">
                    ⛔ CONTRAINDICATED_DRUGS.DAT ({results.filtered_count} FILTERED)
                  </div>
                </div>
                
                <div className="terminal-body">
                  <div className="p-4 bg-red-900 bg-opacity-20 border-2 border-red-500 rounded mb-4">
                    <p className="text-red-400 font-mono text-sm font-bold mb-2">
                      ⚠️ WARNING: These drugs were REMOVED due to contraindications
                    </p>
                    <p className="text-red-300 font-mono text-xs">
                      These medications could be harmful for {results.disease?.name || diseaseName}
                    </p>
                  </div>
                  
                  <div className="space-y-3">
                    {results.filtered_drugs && results.filtered_drugs.map((drug, idx) => (
                      <div key={idx} className="p-4 bg-black bg-opacity-50 border-2 border-red-500 rounded">
                        <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
                          <h3 className="text-xl font-black text-red-400 font-mono">
                            ❌ {drug.drug_name}
                          </h3>
                          <span className={`px-3 py-1 rounded text-xs font-bold font-mono ${
                            drug.severity === 'absolute' 
                              ? 'bg-red-600 text-white' 
                              : 'bg-yellow-600 text-white'
                          }`}>
                            {drug.severity?.toUpperCase()} CONTRAINDICATION
                          </span>
                        </div>
                        <p className="text-red-300 font-mono text-sm">
                          {'>'} REASON: {drug.reason}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Drug Candidates */}
            <div className="terminal-window">
              <div className="terminal-header">
                <div className="text-green-400 font-mono text-sm">
                  REPURPOSING_CANDIDATES.DAT
                </div>
              </div>
              
              <div className="terminal-body">
                {results.candidates && results.candidates.length === 0 ? (
                  <div className="p-6 border-2 border-yellow-500 bg-black bg-opacity-50">
                    <p className="text-yellow-400 font-mono">
                      ⚠️ NO CANDIDATES FOUND WITH SCORE {'>'} {minScore}
                    </p>
                    <p className="text-green-400 font-mono text-sm mt-2">
                      💡 Try lowering minimum score to 0.1 or 0.2
                    </p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {results.candidates && results.candidates.map((candidate, idx) => (
                      <div key={idx} className="drug-card">
                        <div className="flex items-start justify-between mb-4 flex-wrap gap-4">
                          <div className="flex-grow">
                            <div className="flex items-center gap-3 mb-2 flex-wrap">
                              {/* 3D Molecule Visualization */}
                              <div className="molecule-3d">
                                <div className="molecule-atom"></div>
                                <div className="molecule-atom"></div>
                                <div className="molecule-atom"></div>
                              </div>
                              
                              <h3 className="text-3xl font-black text-green-400 font-mono">
                                #{idx + 1} {candidate.drug_name}
                              </h3>
                              <span className={`px-3 py-1 rounded text-xs font-bold font-mono ${getConfidenceBadge(candidate.confidence)}`}>
                                {candidate.confidence?.toUpperCase() || 'N/A'} CONFIDENCE
                              </span>
                            </div>
                            <p className="text-green-300 font-mono text-sm">
                              {'>'} CURRENT_USE: {candidate.indication || candidate.original_indication || 'Unknown'}
                            </p>
                          </div>
                          
                          <div className="score-display">
                            <div className="score-label">MATCH_SCORE</div>
                            <div 
                              className="score-value"
                              style={{ color: getScoreColor(candidate.composite_score || candidate.score || 0) }}
                            >
                              {((candidate.composite_score || candidate.score || 0) * 100).toFixed(0)}%
                            </div>
                          </div>
                        </div>

                        {candidate.mechanism && (
                          <div className="mb-4">
                            <p className="text-green-400 font-mono text-xs mb-2">
                              {'>'} MECHANISM_OF_ACTION:
                            </p>
                            <p className="text-green-300 font-mono text-sm p-3 bg-black bg-opacity-50 border border-green-900">
                              {candidate.mechanism}
                            </p>
                          </div>
                        )}

                        {candidate.explanation && (
                          <div className="mb-4">
                            <p className="text-green-400 font-mono text-xs mb-2">
                              {'>'} REPURPOSING_RATIONALE:
                            </p>
                            <p className="text-green-300 font-mono text-sm p-3 bg-black bg-opacity-50 border border-green-900">
                              {candidate.explanation}
                            </p>
                          </div>
                        )}

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                          <div className="metric-box">
                            <div className="metric-label">GENE_SCORE</div>
                            <div className="metric-value">
                              {((candidate.gene_target_score || candidate.gene_score || 0) * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div className="metric-box">
                            <div className="metric-label">PATHWAY_SCORE</div>
                            <div className="metric-value">
                              {((candidate.pathway_overlap_score || candidate.pathway_score || 0) * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div className="metric-box">
                            <div className="metric-label">SHARED_GENES</div>
                            <div className="metric-value">
                              {candidate.shared_genes?.length || 0}
                            </div>
                          </div>
                          <div className="metric-box">
                            <div className="metric-label">SHARED_PATHWAYS</div>
                            <div className="metric-value">
                              {candidate.shared_pathways?.length || 0}
                            </div>
                          </div>
                        </div>

                        {candidate.shared_genes && candidate.shared_genes.length > 0 && (
                          <div className="mb-3">
                            <p className="text-green-400 font-mono text-xs mb-2">
                              {'>'} SHARED_TARGET_GENES:
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {candidate.shared_genes.map((gene) => (
                                <span key={gene} className="gene-badge-small">
                                  {gene}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {candidate.shared_pathways && candidate.shared_pathways.length > 0 && (
                          <div className="mb-4">
                            <p className="text-green-400 font-mono text-xs mb-2">
                              {'>'} SHARED_BIOLOGICAL_PATHWAYS:
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {candidate.shared_pathways.map((pathway) => (
                                <span key={pathway} className="pathway-badge">
                                  {pathway}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Clinical Validation Button */}
                        <div className="mt-4 pt-4 border-t border-green-900">
                          {!clinicalResults[idx] && (
                            <button
                              onClick={() => handleClinicalValidation(candidate, idx)}
                              disabled={validatingIndex === idx}
                              className="w-full px-4 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-mono font-bold rounded border-2 border-cyan-400 hover:from-cyan-500 hover:to-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {validatingIndex === idx ? (
                                <span className="flex items-center justify-center gap-2">
                                  <span className="loader-small"></span>
                                  VALIDATING CLINICALLY...
                                </span>
                              ) : (
                                '🔬 VALIDATE CLINICALLY'
                              )}
                            </button>
                          )}

                          {/* Clinical Validation Results */}
                          {clinicalResults[idx] && !clinicalResults[idx].error && (
                            <div className="mt-4 space-y-4">
                              <div className="p-4 bg-gradient-to-r from-cyan-900 to-blue-900 border-2 border-cyan-400 rounded">
                                <h4 className="text-cyan-300 font-mono font-bold mb-3 flex items-center gap-2">
                                  🏥 CLINICAL VALIDATION RESULTS
                                </h4>
                                
                                {/* Risk Level */}
                                <div className="mb-4 p-3 bg-black bg-opacity-50 rounded border-2" style={{borderColor: getRiskColor(clinicalResults[idx].risk_level)}}>
                                  <div className="flex items-center justify-between">
                                    <span className="text-white font-mono text-sm">RISK LEVEL:</span>
                                    <span 
                                      className="font-mono font-black text-xl"
                                      style={{color: getRiskColor(clinicalResults[idx].risk_level)}}
                                    >
                                      {clinicalResults[idx].risk_level}
                                    </span>
                                  </div>
                                </div>

                                {/* Recommendation */}
                                <div className="mb-4 p-3 bg-black bg-opacity-50 rounded">
                                  <p className="text-cyan-200 font-mono text-sm font-bold">
                                    {clinicalResults[idx].recommendation}
                                  </p>
                                </div>

                                {/* Evidence Summary */}
                                <div className="mb-4">
                                  <p className="text-cyan-300 font-mono text-xs mb-2">EVIDENCE SUMMARY:</p>
                                  <div className="space-y-1">
                                    {clinicalResults[idx].evidence_summary?.map((item, i) => (
                                      <p key={i} className="text-cyan-100 font-mono text-xs">
                                        {item}
                                      </p>
                                    ))}
                                  </div>
                                </div>

                                {/* Detailed Results */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  {/* Clinical Trials */}
                                  {clinicalResults[idx].clinical_trials && (
                                    <div className="p-3 bg-black bg-opacity-50 rounded border border-cyan-700">
                                      <p className="text-cyan-300 font-mono text-xs font-bold mb-2">📋 CLINICAL TRIALS:</p>
                                      <p className="text-cyan-100 font-mono text-xs">
                                        {clinicalResults[idx].clinical_trials.summary || 'No trials found'}
                                      </p>
                                      {clinicalResults[idx].clinical_trials.trials?.length > 0 && (
                                        <div className="mt-2 space-y-1">
                                          {clinicalResults[idx].clinical_trials.trials.slice(0, 3).map((trial, i) => (
                                            <div key={i} className="text-cyan-200 font-mono text-xs">
                                              • {trial.phase} - {trial.status}
                                            </div>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  )}

                                  {/* Literature */}
                                  {clinicalResults[idx].literature_evidence && (
                                    <div className="p-3 bg-black bg-opacity-50 rounded border border-cyan-700">
                                      <p className="text-cyan-300 font-mono text-xs font-bold mb-2">📚 LITERATURE:</p>
                                      <p className="text-cyan-100 font-mono text-xs">
                                        {clinicalResults[idx].literature_evidence.summary || 'No literature found'}
                                      </p>
                                    </div>
                                  )}

                                  {/* Safety */}
                                  {clinicalResults[idx].safety_signals && (
                                    <div className="p-3 bg-black bg-opacity-50 rounded border border-cyan-700">
                                      <p className="text-cyan-300 font-mono text-xs font-bold mb-2">⚠️ SAFETY:</p>
                                      <p className="text-cyan-100 font-mono text-xs">
                                        {clinicalResults[idx].safety_signals.summary || 'No safety data'}
                                      </p>
                                    </div>
                                  )}

                                  {/* Mechanism */}
                                  {clinicalResults[idx].mechanism_analysis && (
                                    <div className="p-3 bg-black bg-opacity-50 rounded border border-cyan-700">
                                      <p className="text-cyan-300 font-mono text-xs font-bold mb-2">⚙️ MECHANISM:</p>
                                      <p className="text-cyan-100 font-mono text-xs">
                                        {clinicalResults[idx].mechanism_analysis.summary || 'Unknown'}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Error Display */}
                          {clinicalResults[idx]?.error && (
                            <div className="mt-4 p-4 bg-red-900 bg-opacity-30 border-2 border-red-500 rounded">
                              <p className="text-red-400 font-mono text-sm">
                                ❌ Validation Error: {clinicalResults[idx].error}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="text-center py-8 relative z-10">
        <p className="text-green-400 font-mono text-sm">
          POWERED BY: OpenTargets • ChEMBL • DGIdb • ClinicalTrials.gov • PubMed • OpenFDA
        </p>
      </div>
    </div>
  );
}

export default App;