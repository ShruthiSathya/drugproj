import React, { useState } from 'react';
import './App.css';

function App() {
  const [diseaseName, setDiseaseName] = useState('');
  const [topK, setTopK] = useState(10);
  const [minScore, setMinScore] = useState(0.2); // Lowered default
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [streamingStatus, setStreamingStatus] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);
    setStreamingStatus('Starting analysis...');

    try {
      const response = await fetch('http://localhost:8000/api/repurpose/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          disease_name: diseaseName,
          top_k: topK,
          min_score: minScore,
          anthropic_api_key: apiKey || null,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            
            if (data.stage === 'fetching') {
              setStreamingStatus(data.message);
            } else if (data.stage === 'disease_found') {
              setStreamingStatus(`Found: ${data.data.name} (${data.data.gene_count} genes, ${data.data.pathway_count} pathways)`);
            } else if (data.stage === 'graph_building') {
              setStreamingStatus(data.message);
            } else if (data.stage === 'graph_built') {
              setStreamingStatus(`Graph built: ${data.data.total_nodes} nodes, ${data.data.total_edges} edges`);
            } else if (data.stage === 'scoring') {
              setStreamingStatus(data.message);
            } else if (data.stage === 'scored') {
              setStreamingStatus(data.message);
            } else if (data.stage === 'explaining') {
              setStreamingStatus(data.message);
            } else if (data.stage === 'complete') {
              setResults(data.data);
              setStreamingStatus('Analysis complete!');
            } else if (data.stage === 'error') {
              setError(data.message);
              setStreamingStatus('');
            } else if (data.stage === 'warning') {
              setStreamingStatus(data.message);
            }
          }
        }
      }
    } catch (err) {
      setError(err.message);
      setStreamingStatus('');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.7) return '#10b981';
    if (score >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  const getConfidenceBadge = (confidence) => {
    const colors = {
      High: 'bg-green-100 text-green-800',
      Medium: 'bg-yellow-100 text-yellow-800',
      Low: 'bg-red-100 text-red-800',
    };
    return colors[confidence] || colors.Low;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-black mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600">
            🧬 AI Drug Repurposing Engine
          </h1>
          <p className="text-gray-600 text-xl">
            Discover FDA-approved drugs for new therapeutic applications
          </p>
        </div>

        {/* Input Form */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-bold text-gray-800 mb-2">
                🔬 Disease Name
              </label>
              <input
                type="text"
                value={diseaseName}
                onChange={(e) => setDiseaseName(e.target.value)}
                placeholder="e.g., Parkinson's Disease, Alzheimer's, Breast Cancer"
                className="w-full px-6 py-4 border-2 border-purple-200 rounded-xl focus:border-purple-500 focus:ring-4 focus:ring-purple-200/50 transition-all outline-none text-lg"
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-bold text-gray-800 mb-2">
                  📊 Number of Candidates
                </label>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  min="1"
                  max="20"
                  className="w-full px-6 py-4 border-2 border-blue-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-200/50 transition-all outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-gray-800 mb-2">
                  🎯 Minimum Score
                </label>
                <input
                  type="number"
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  min="0"
                  max="1"
                  step="0.1"
                  className="w-full px-6 py-4 border-2 border-green-200 rounded-xl focus:border-green-500 focus:ring-4 focus:ring-green-200/50 transition-all outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-800 mb-2">
                🔑 Anthropic API Key (Optional)
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-ant-..."
                className="w-full px-6 py-4 border-2 border-pink-200 rounded-xl focus:border-pink-500 focus:ring-4 focus:ring-pink-200/50 transition-all outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 text-white py-5 px-8 rounded-xl font-bold text-xl hover:shadow-2xl hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none transition-all duration-300"
            >
              {loading ? '⚡ Analyzing...' : '🚀 Find Repurposing Candidates'}
            </button>
          </form>

          {streamingStatus && (
            <div className="mt-6 p-5 bg-blue-50 border-l-4 border-blue-500 rounded-xl">
              <p className="text-blue-700 font-semibold">{streamingStatus}</p>
            </div>
          )}

          {error && (
            <div className="mt-6 p-5 bg-red-50 border-l-4 border-red-500 rounded-xl">
              <p className="text-red-700 font-semibold">❌ Error: {error}</p>
            </div>
          )}
        </div>

        {/* Results */}
        {results && (
          <div className="space-y-8">
            {/* Disease Info */}
            <div className="bg-white rounded-2xl shadow-xl p-8">
              <h2 className="text-4xl font-black text-gray-800 mb-6">
                {results.disease_name}
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div className="bg-gradient-to-br from-blue-400 to-blue-600 rounded-xl p-6 text-white shadow-lg">
                  <p className="text-sm opacity-90 mb-2">Associated Genes</p>
                  <p className="text-4xl font-black">{results.disease_genes.length}</p>
                </div>
                <div className="bg-gradient-to-br from-purple-400 to-purple-600 rounded-xl p-6 text-white shadow-lg">
                  <p className="text-sm opacity-90 mb-2">Pathways</p>
                  <p className="text-4xl font-black">{results.disease_pathways.length}</p>
                </div>
                <div className="bg-gradient-to-br from-green-400 to-green-600 rounded-xl p-6 text-white shadow-lg">
                  <p className="text-sm opacity-90 mb-2">Candidates Found</p>
                  <p className="text-4xl font-black">{results.candidates.length}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-bold text-gray-800 mb-3 text-lg">🧬 Top Genes</h3>
                  <div className="flex flex-wrap gap-2">
                    {results.disease_genes.slice(0, 10).map((gene) => (
                      <span key={gene} className="px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                        {gene}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="font-bold text-gray-800 mb-3 text-lg">🔬 Key Pathways</h3>
                  <div className="flex flex-wrap gap-2">
                    {results.disease_pathways.slice(0, 5).map((pathway) => (
                      <span key={pathway} className="px-4 py-2 bg-purple-100 text-purple-800 rounded-full text-sm font-semibold">
                        {pathway}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Drug Candidates */}
            <div>
              <h2 className="text-4xl font-black text-gray-800 mb-6">
                💊 Drug Repurposing Candidates
              </h2>
              {results.candidates.length === 0 ? (
                <div className="bg-yellow-50 border-l-4 border-yellow-500 p-6 rounded-xl">
                  <p className="text-yellow-800 font-semibold">
                    ⚠️ No candidates found with minimum score of {minScore}. Try lowering the minimum score to 0.1 or 0.2.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {results.candidates.map((candidate, idx) => (
                    <div
                      key={candidate.drug_id}
                      className="bg-white rounded-2xl shadow-xl p-6"
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-grow">
                          <div className="flex items-center gap-3 mb-2 flex-wrap">
                            <h3 className="text-3xl font-black text-gray-800">
                              #{idx + 1}. {candidate.drug_name}
                            </h3>
                            <span className={`px-4 py-1 rounded-full text-sm font-bold ${getConfidenceBadge(candidate.confidence)}`}>
                              {candidate.confidence} Confidence
                            </span>
                          </div>
                          <p className="text-gray-600 font-medium">
                            💼 Current Use: {candidate.original_indication}
                          </p>
                        </div>
                        <div className="text-right ml-4">
                          <p className="text-sm text-gray-600 mb-1 font-semibold">Score</p>
                          <p
                            className="text-5xl font-black"
                            style={{ color: getScoreColor(candidate.composite_score) }}
                          >
                            {(candidate.composite_score * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>

                      <div className="mb-4">
                        <p className="text-sm font-bold text-gray-800 mb-2">⚙️ Mechanism</p>
                        <p className="text-gray-700 bg-gray-50 p-4 rounded-xl">{candidate.mechanism}</p>
                      </div>

                      {candidate.explanation && (
                        <div className="mb-4">
                          <p className="text-sm font-bold text-gray-800 mb-2">🎯 Why This Might Work</p>
                          <p className="text-gray-700 bg-blue-50 p-4 rounded-xl">{candidate.explanation}</p>
                        </div>
                      )}

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                        <div className="bg-blue-100 rounded-xl p-4 text-center">
                          <p className="text-xs text-blue-900 mb-1 font-bold">Gene Targeting</p>
                          <p className="text-2xl font-black text-blue-900">
                            {(candidate.gene_target_score * 100).toFixed(0)}%
                          </p>
                        </div>
                        <div className="bg-purple-100 rounded-xl p-4 text-center">
                          <p className="text-xs text-purple-900 mb-1 font-bold">Pathway Overlap</p>
                          <p className="text-2xl font-black text-purple-900">
                            {(candidate.pathway_overlap_score * 100).toFixed(0)}%
                          </p>
                        </div>
                        <div className="bg-green-100 rounded-xl p-4 text-center">
                          <p className="text-xs text-green-900 mb-1 font-bold">Shared Genes</p>
                          <p className="text-2xl font-black text-green-900">{candidate.shared_genes.length}</p>
                        </div>
                        <div className="bg-pink-100 rounded-xl p-4 text-center">
                          <p className="text-xs text-pink-900 mb-1 font-bold">Shared Pathways</p>
                          <p className="text-2xl font-black text-pink-900">{candidate.shared_pathways.length}</p>
                        </div>
                      </div>

                      {candidate.shared_genes.length > 0 && (
                        <div className="mb-3">
                          <p className="text-sm font-bold text-gray-800 mb-2">🎯 Shared Target Genes</p>
                          <div className="flex flex-wrap gap-2">
                            {candidate.shared_genes.map((gene) => (
                              <span key={gene} className="px-3 py-1 bg-green-100 text-green-900 rounded-lg text-xs font-bold">
                                {gene}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {candidate.shared_pathways.length > 0 && (
                        <div>
                          <p className="text-sm font-bold text-gray-800 mb-2">🔬 Shared Pathways</p>
                          <div className="flex flex-wrap gap-2">
                            {candidate.shared_pathways.map((pathway) => (
                              <span key={pathway} className="px-3 py-1 bg-purple-100 text-purple-900 rounded-lg text-xs font-bold">
                                {pathway}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;