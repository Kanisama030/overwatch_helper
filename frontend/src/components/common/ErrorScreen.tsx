export function ErrorScreen({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-screen" style={{ backgroundColor: '#221910' }}>
      <div className="text-center max-w-md px-4">
        <span className="material-symbols-outlined text-5xl mb-4 block" style={{ color: '#ef4444' }}>error</span>
        <h2 className="text-xl font-bold text-white mb-2">Failed to load data</h2>
        <p className="text-gray-400 text-sm">{message}</p>
      </div>
    </div>
  );
}
