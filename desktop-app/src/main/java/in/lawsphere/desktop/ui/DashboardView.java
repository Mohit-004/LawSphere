package in.lawsphere.desktop.ui;

import in.lawsphere.desktop.api.ModelList;
import in.lawsphere.desktop.api.SystemStatus;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.ListView;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.VBox;

public final class DashboardView extends BorderPane {
    private final Label apiValue = new Label("Starting…");
    private final Label sqliteValue = new Label("—");
    private final Label ollamaValue = new Label("—");
    private final Label summary = new Label("Connecting to the local AI service");
    private final Label error = new Label();
    private final ListView<String> models = new ListView<>();
    private final Button refreshButton = new Button("Refresh status");

    public DashboardView() {
        getStyleClass().add("app-root");
        setTop(createHeader());
        setCenter(createContent());
        setBottom(createFooter());
    }

    private HBox createHeader() {
        Label brand = new Label("LawSphere");
        brand.getStyleClass().add("brand");
        Label subtitle = new Label("Private, local legal research workspace");
        subtitle.getStyleClass().add("subtitle");

        VBox titles = new VBox(5, brand, subtitle);
        refreshButton.getStyleClass().add("secondary-button");
        HBox header = new HBox(titles, refreshButton);
        header.setAlignment(Pos.CENTER_LEFT);
        header.setSpacing(24);
        header.setPadding(new Insets(28, 36, 26, 36));
        HBox.setHgrow(titles, Priority.ALWAYS);
        return header;
    }

    private VBox createContent() {
        Label heading = new Label("System overview");
        heading.getStyleClass().add("section-heading");
        summary.getStyleClass().add("summary");

        HBox cards = new HBox(14,
                createStatusCard("AI service", apiValue),
                createStatusCard("Local database", sqliteValue),
                createStatusCard("Ollama runtime", ollamaValue));
        for (var child : cards.getChildren()) {
            HBox.setHgrow(child, Priority.ALWAYS);
        }

        Label modelsHeading = new Label("Installed local models");
        modelsHeading.getStyleClass().add("section-heading");
        models.setPlaceholder(new Label("Model names will appear here when Ollama is available."));
        models.getStyleClass().add("model-list");
        VBox.setVgrow(models, Priority.ALWAYS);

        error.getStyleClass().add("error-message");
        error.setWrapText(true);
        VBox content = new VBox(18, heading, summary, cards, modelsHeading, models, error);
        content.setPadding(new Insets(12, 36, 24, 36));
        VBox.setVgrow(models, Priority.ALWAYS);
        return content;
    }

    private VBox createStatusCard(String title, Label value) {
        Label label = new Label(title);
        label.getStyleClass().add("card-title");
        value.getStyleClass().add("card-value");
        VBox card = new VBox(12, label, value);
        card.getStyleClass().add("status-card");
        card.setPadding(new Insets(18));
        card.setMinHeight(100);
        return card;
    }

    private HBox createFooter() {
        Label privacy = new Label("Your documents and questions stay on this device.");
        privacy.getStyleClass().add("footer-text");
        HBox footer = new HBox(privacy);
        footer.setPadding(new Insets(14, 36, 18, 36));
        return footer;
    }

    public void setRefreshHandler(Runnable handler) {
        refreshButton.setOnAction(event -> handler.run());
    }

    public void setLoading(boolean loading) {
        refreshButton.setDisable(loading);
        refreshButton.setText(loading ? "Checking…" : "Refresh status");
        if (loading) {
            summary.setText("Connecting to the local AI service");
            error.setText("");
        }
    }

    public void show(SystemStatus status, ModelList modelList) {
        apiValue.setText(status.status().toUpperCase());
        sqliteValue.setText(status.sqlite().toUpperCase());
        ollamaValue.setText(modelList.ollama().toUpperCase());
        summary.setText(modelList.models().isEmpty()
                ? "Service is ready. No Ollama models are currently installed."
                : "Service is ready with " + modelList.models().size() + " local model(s).");
        models.getItems().setAll(modelList.models());
        error.setText("");
    }

    public void showError(String message) {
        apiValue.setText("UNAVAILABLE");
        summary.setText("The local AI service could not be reached.");
        error.setText(message + System.lineSeparator() + System.lineSeparator()
                + "From the project folder, run .\\scripts\\setup-python.ps1 to install backend dependencies. "
                + "See README.md for Python, Java, and Maven prerequisites.");
    }
}
