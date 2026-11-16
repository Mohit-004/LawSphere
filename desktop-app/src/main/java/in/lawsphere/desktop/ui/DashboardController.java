package in.lawsphere.desktop.ui;

import in.lawsphere.desktop.api.LocalAiClient;
import in.lawsphere.desktop.api.ModelList;
import in.lawsphere.desktop.api.SystemStatus;
import in.lawsphere.desktop.service.AiEngineProcessManager;
import javafx.concurrent.Task;

public final class DashboardController {
    private final DashboardView view;
    private final LocalAiClient client;
    private final AiEngineProcessManager processManager;

    public DashboardController(
            DashboardView view,
            LocalAiClient client,
            AiEngineProcessManager processManager) {
        this.view = view;
        this.client = client;
        this.processManager = processManager;
    }

    public void initialize() {
        view.setRefreshHandler(this::refresh);
        refresh();
    }

    private void refresh() {
        view.setLoading(true);
        Task<DashboardData> task = new Task<>() {
            @Override
            protected DashboardData call() {
                processManager.startIfNeeded();
                return new DashboardData(client.getSystemStatus(), client.getModels());
            }
        };
        task.setOnSucceeded(event -> {
            DashboardData data = task.getValue();
            view.show(data.status(), data.models());
            view.setLoading(false);
        });
        task.setOnFailed(event -> {
            Throwable failure = task.getException();
            view.showError(failure == null ? "Unknown local service error" : failure.getMessage());
            view.setLoading(false);
        });
        Thread worker = new Thread(task, "lawsphere-service-check");
        worker.setDaemon(true);
        worker.start();
    }

    private record DashboardData(SystemStatus status, ModelList models) {
    }
}
