import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Topic } from '../lib/api'

interface TopicListProps {
  topics: Topic[]
}

const TopicList: React.FC<TopicListProps> = ({ topics }) => {
  if (topics.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
        No topics available. Select a country and click "Load Trends".
      </div>
    )
  }

  // Prepare data for chart
  const chartData = topics.map((topic) => ({
    name: topic.label.length > 30 ? topic.label.substring(0, 30) + '...' : topic.label,
    count: topic.count,
    fullLabel: topic.label,
  }))

  return (
    <div>
      {/* Chart */}
      <div style={{ marginBottom: '2rem', backgroundColor: 'white', padding: '1rem', borderRadius: '8px' }}>
        <h3 style={{ marginBottom: '1rem', color: '#213547' }}>Trending Topics Overview</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#646cff" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* List */}
      <div>
        <h3 style={{ marginBottom: '1rem' }}>Detailed Topics</h3>
        <div style={{ display: 'grid', gap: '1rem' }}>
          {topics.map((topic) => (
            <div
              key={topic.id}
              style={{
                backgroundColor: 'white',
                padding: '1.5rem',
                borderRadius: '8px',
                border: '1px solid #e0e0e0',
                color: '#213547',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                <h4 style={{ margin: 0, fontSize: '1.2rem', flex: 1 }}>{topic.label}</h4>
                <span
                  style={{
                    backgroundColor: '#646cff',
                    color: 'white',
                    padding: '0.25rem 0.75rem',
                    borderRadius: '12px',
                    fontSize: '0.9rem',
                    fontWeight: 600,
                    marginLeft: '1rem',
                  }}
                >
                  {topic.count}
                </span>
              </div>

              <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.5rem' }}>
                <strong>Sources:</strong> {topic.sources.join(', ')}
                <span style={{ marginLeft: '1rem' }}>
                  <strong>Confidence:</strong> {(topic.confidence * 100).toFixed(0)}%
                </span>
              </div>

              {topic.sample_titles.length > 0 && (
                <div style={{ fontSize: '0.85rem', color: '#666' }}>
                  <strong>Sample Titles:</strong>
                  <ul style={{ marginTop: '0.25rem', marginLeft: '1.5rem' }}>
                    {topic.sample_titles.map((title, idx) => (
                      <li key={idx}>{title}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default TopicList
