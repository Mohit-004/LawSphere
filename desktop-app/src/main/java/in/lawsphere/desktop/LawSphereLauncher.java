package in.lawsphere.desktop;

import in.lawsphere.desktop.api.LocalAiClient;
import in.lawsphere.desktop.api.SystemStatus;
import in.lawsphere.desktop.service.AiEngineProcessManager;

public final class LawSphereLauncher {
    private LawSphereLauncher() {
    }

    public static void main(String[] args) {
        LocalAiClient client = new LocalAiClient();
        try (AiEngineProcessManager processManager = new AiEngineProcessManager(client)) {
            processManager.startIfNeeded();
            SystemStatus status = client.getSystemStatus();
            System.out.printf(
                    "%s %s | API: %s | SQLite: %s | Ollama: %s (%d models)%n",
                    status.appName(), status.version(), status.status(), status.sqlite(),
                    status.ollama(), status.installedModelCount());
        }
    }
}
