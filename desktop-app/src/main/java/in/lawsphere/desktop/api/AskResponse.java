package in.lawsphere.desktop.api;

import java.util.List;

public record AskResponse(
        String query,
        String answer,
        String chatModel,
        String embeddingModel,
        List<SourceCitation> sources) {
}
