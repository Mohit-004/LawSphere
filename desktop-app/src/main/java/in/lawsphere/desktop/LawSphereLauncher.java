package in.lawsphere.desktop;

import in.lawsphere.desktop.api.LocalAiClient;
import in.lawsphere.desktop.api.SystemStatus;

import java.net.URI;

public final class LawSphereLauncher {
    private LawSphereLauncher() {
    }

    public static void main(String[] args) {
        LocalAiClient client = args.length == 0
                ? new LocalAiClient()
                : new LocalAiClient(URI.create(args[0]));
        SystemStatus status = client.getSystemStatus();
        System.out.printf(
                "%s %s | API: %s | SQLite: %s | Ollama: %s (%d models)%n",
                status.appName(), status.version(), status.status(), status.sqlite(),
                status.ollama(), status.installedModelCount());
    }
}
