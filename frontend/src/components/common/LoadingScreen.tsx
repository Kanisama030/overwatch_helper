export function LoadingScreen() {
  return (
    <div className="flex items-center justify-center h-screen" style={{ backgroundColor: '#221910' }}>
      <div className="text-center">
        <div className="text-4xl font-black mb-4" style={{ color: '#f27f0d' }}>OW</div>
        <p className="text-gray-400 text-sm">Loading data...</p>
      </div>
    </div>
  );
}
