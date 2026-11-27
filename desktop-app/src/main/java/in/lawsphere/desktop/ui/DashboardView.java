package in.lawsphere.desktop.ui;

import in.lawsphere.desktop.api.AskResponse;
import in.lawsphere.desktop.api.ModelList;
import in.lawsphere.desktop.api.SystemStatus;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.ListView;
import javafx.scene.control.Tab;
import javafx.scene.control.TabPane;
import javafx.scene.control.TextArea;
import javafx.scene.control.TextField;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.VBox;

import java.util.function.Consumer;

public final class DashboardView extends BorderPane {
    private final Label apiValue = new Label("Starting…");
    private final Label sqliteValue = new Label("—");
    private final Label ollamaValue = new Label("—");
    private final Label summary = new Label("Connecting to the local AI service");
    private final Label error = new Label();
    private final ListView<String> models = new ListView<>();
    private final Button refreshButton = new Button("Refresh status");
    private final TextField question = new TextField();
    private final Button askButton = new Button("Ask local sources");
    private final TextArea answer = new TextArea();
    private final ListView<String> citations = new ListView<>();
    private final Label askError = new Label();

    public DashboardView() {
        getStyleClass().add("app-root");
        setTop(createHeader());
        setCenter(createTabs());
        setBottom(createFooter());
    }

    private TabPane createTabs() {
        TabPane tabs = new TabPane();
        Tab overview = new Tab("System overview", createContent());
        overview.setClosable(false);
        Tab ask = new Tab("Ask", createAskContent());
        ask.setClosable(false);
        tabs.getTabs().setAll(overview, ask);
        return tabs;
    }

    private VBox createAskContent() {
        Label heading = new Label("Ask your indexed sources");
        heading.getStyleClass().add("section-heading");
        Label note = new Label("Answers use local Ollama models and include the retrieved source passages.");
        note.getStyleClass().add("subtitle");
        question.setPromptText("Ask a question about your indexed legal materials");
        askButton.getStyleClass().add("secondary-button");
        answer.setEditable(false);
        answer.setWrapText(true);
        answer.setPromptText("Your answer will appear here.");
        VBox.setVgrow(answer, Priority.ALWAYS);
        citations.setPlaceholder(new Label("Source passages will appear here."));
        VBox.setVgrow(citations, Priority.ALWAYS);
        askError.getStyleClass().add("error-message");
        askError.setWrapText(true);
        VBox content = new VBox(12, heading, note, question, askButton, askError,
                new Label("Answer"), answer, new Label("Retrieved sources"), citations);
        content.setPadding(new Insets(20, 36, 24, 36));
        VBox.setVgrow(answer, Priority.ALWAYS);
        VBox.setVgrow(citations, Priority.ALWAYS);
        return content;
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

    public void setAskHandler(Consumer<String> handler) {
        askButton.setOnAction(event -> handler.accept(question.getText()));
        question.setOnAction(event -> handler.accept(question.getText()));
    }

    public void setAskLoading(boolean loading) {
        askButton.setDisable(loading);
        question.setDisable(loading);
        askButton.setText(loading ? "Searching and generating…" : "Ask local sources");
        if (loading) {
            askError.setText("");
        }
    }

    public void showAnswer(AskResponse response) {
        answer.setText(response.answer());
        citations.getItems().setAll(java.util.stream.IntStream.range(0, response.sources().size())
                .mapToObj(index -> formatCitation(index + 1, response.sources().get(index)))
                .toList());
        askError.setText("");
    }

    private String formatCitation(int index, in.lawsphere.desktop.api.SourceCitation source) {
        String location = source.pageNumber() == null ? "" : " · page " + source.pageNumber();
        String reference = source.source() == null || source.source().isBlank()
                ? source.title()
                : source.title() + " · " + source.source();
        return "[S" + index + "] " + reference + location + System.lineSeparator() + source.text();
    }

    public void showAskError(String message) {
        askError.setText(message);
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
