package in.lawsphere.desktop;

import javafx.application.Application;

/** Classpath-safe entry point for Maven and jpackage launchers. */
public final class LawSphereLauncher {
    private LawSphereLauncher() {
    }

    public static void main(String[] args) {
        Application.launch(LawSphereApplication.class, args);
    }
}
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

    public static void main(String[] args) {
        launch(args);
    }
}
