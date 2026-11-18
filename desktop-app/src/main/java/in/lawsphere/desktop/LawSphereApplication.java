package in.lawsphere.desktop;

import in.lawsphere.desktop.api.LocalAiClient;
import in.lawsphere.desktop.service.AiEngineProcessManager;
import in.lawsphere.desktop.ui.DashboardController;
import in.lawsphere.desktop.ui.DashboardView;
import javafx.application.Application;
import javafx.scene.Scene;
import javafx.stage.Stage;

public final class LawSphereApplication extends Application {
    private AiEngineProcessManager processManager;

    @Override
    public void start(Stage stage) {
        LocalAiClient client = new LocalAiClient();
        processManager = new AiEngineProcessManager(client);

        DashboardView view = new DashboardView();
        DashboardController controller = new DashboardController(view, client, processManager);
        controller.initialize();

        Scene scene = new Scene(view, 1040, 700);
        var stylesheet = getClass().getResource("/styles/dashboard.css");
        if (stylesheet != null) {
            scene.getStylesheets().add(stylesheet.toExternalForm());
        }

        stage.setTitle("LawSphere");
        stage.setMinWidth(820);
        stage.setMinHeight(580);
        stage.setScene(scene);
        stage.show();
    }

    @Override
    public void stop() {
        if (processManager != null) {
            processManager.close();
        }
    }
}
