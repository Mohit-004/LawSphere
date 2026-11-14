package in.lawsphere.desktop.api;

public record SystemStatus(
        String appName,
        String version,
        String status,
        boolean offlineMode,
        String sqlite,
        String ollama,
        int installedModelCount) {
}
