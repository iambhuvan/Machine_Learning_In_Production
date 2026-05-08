import $ from "jquery";
import assert from "minimalistic-assert";

import render_inline_decorated_channel_name from "../templates/inline_decorated_channel_name.hbs";
import render_message_view_header from "../templates/message_view_header.hbs";

import type { Filter } from "./filter.ts";
import * as hash_util from "./hash_util.ts";
import { $t, $t_html } from "./i18n.ts";
import * as inbox_util from "./inbox_util.ts";
import * as narrow_state from "./narrow_state.ts";
import { page_params } from "./page_params.ts";
import * as peer_data from "./peer_data.ts";
import * as recent_view_util from "./recent_view_util.ts";
import * as rendered_markdown from "./rendered_markdown.ts";
import * as search from "./search.ts";
import { current_user } from "./state_data.ts";
import * as stream_data from "./stream_data.ts";
import type { StreamSubscription } from "./sub_store.ts";
import * as channel from "./channel.ts";
import * as dialog_widget from "./dialog_widget.ts";
import * as markdown from "./markdown.ts";

type MessageViewHeaderContext = {
    title?: string | undefined;
    title_html?: string | undefined;
    description?: string;
    link?: string;
    is_spectator?: boolean;
    sub_count?: string | number;
    formatted_sub_count?: string;
    rendered_narrow_description?: string;
    is_admin?: boolean;
    stream?: StreamSubscription;
    stream_settings_link?: string;
    show_recap_button?: boolean;
    stream_name?: string;
    topic_name?: string;
} & (
        | {
            zulip_icon: string;
        }
        | {
            icon: string | undefined;
        }
    );

function get_message_view_header_context(filter: Filter | undefined): MessageViewHeaderContext {
    if (recent_view_util.is_visible()) {
        return {
            title: $t({ defaultMessage: "Recent conversations" }),
            description: $t({ defaultMessage: "Overview of ongoing conversations." }),
            zulip_icon: "recent",
            link: "/help/recent-conversations",
        };
    }

    if (inbox_util.is_visible() && !inbox_util.is_channel_view()) {
        return {
            title: $t({ defaultMessage: "Inbox" }),
            description: $t({
                defaultMessage: "Overview of your conversations with unread messages.",
            }),
            zulip_icon: "inbox",
            link: "/help/inbox",
        };
    }

    // TODO: If we're not in the recent or inbox view, there should be
    // a message feed with a declared filter in the center pane. But
    // because of an initialization order bug, this function gets
    // called with a filter of `undefined` when loading the web app
    // with, say, inbox as the home view.
    //
    // TODO: Refactor this function to move the inbox/recent cases
    // into the caller, and this function can always get a Filter object.
    //
    // TODO: This ideally doesn't need a special case, we can just use
    // `filter.get_description` for it.
    if (filter === undefined || filter.is_in_home()) {
        let description;
        if (page_params.is_spectator) {
            description = $t({
                defaultMessage: "All your messages.",
            });
        } else {
            description = $t({
                defaultMessage: "All your messages except those in muted channels and topics.",
            });
        }
        return {
            title: $t({ defaultMessage: "Combined feed" }),
            description,
            zulip_icon: "all-messages",
            link: "/help/combined-feed",
        };
    }

    const title = filter.get_title();
    const description = filter.get_description()?.description;
    const link = filter.get_description()?.link;
    assert(title !== undefined);
    let context = filter.add_icon_data({
        title,
        description,
        link,
        is_spectator: page_params.is_spectator,
    });

    if (filter.has_operator("channel")) {
        const current_stream = stream_data.get_sub_by_id_string(
            filter.terms_with_operator("channel")[0]!.operand,
        );
        if (!current_stream) {
            return {
                ...context,
                sub_count: "0",
                formatted_sub_count: "0",
                rendered_narrow_description: $t({
                    defaultMessage: "This channel does not exist or is private.",
                }),
            };
        }

        if (inbox_util.is_visible() && inbox_util.is_channel_view()) {
            const stream_name_with_privacy_symbol_html = render_inline_decorated_channel_name({
                stream: current_stream,
                show_colored_icon: true,
            });
            context = {
                ...context,
                title: undefined,
                title_html: stream_name_with_privacy_symbol_html,
                // We don't want to show an initial icon here.
                icon: undefined,
                zulip_icon: undefined,
            };
        }

        // We can now be certain that the narrow
        // involves a stream which exists and
        // the current user can access.
        const sub_count = peer_data.get_subscriber_count(current_stream.stream_id);
        const context_data: MessageViewHeaderContext = {
            ...context,
            is_admin: current_user.is_admin,
            rendered_narrow_description: current_stream.rendered_description,
            sub_count,
            stream: current_stream,
            stream_settings_link: hash_util.channels_settings_edit_url(current_stream, "general"),
        };

        if (filter.has_operator("topic")) {
            context_data.show_recap_button = true;
            context_data.topic_name = filter.terms_with_operator("topic")[0]!.operand;
            context_data.stream_name = current_stream.name;
        }

        return context_data;
    }

    return context;
}

export function colorize_message_view_header(): void {
    const current_sub = narrow_state.stream_sub();
    if (!current_sub) {
        return;
    }
    // selecting i instead of .fa because web public streams have custom icon.
    $("#message_view_header a.stream i").css("color", current_sub.color);
}

function append_and_display_title_area(context: MessageViewHeaderContext): void {
    const $message_view_header_elem = $("#message_view_header");
    $message_view_header_elem.html(render_message_view_header(context));
    if (context.stream_settings_link) {
        colorize_message_view_header();
    }
    $message_view_header_elem.removeClass("notdisplayed");
    const $content = $message_view_header_elem.find("span.rendered_markdown");
    if ($content) {
        // Update syntax like stream names, emojis, mentions, timestamps.
        rendered_markdown.update_elements($content);
    }
}

function build_message_view_header(filter: Filter | undefined): void {
    // This makes sure we don't waste time appending
    // message_view_header on a template where it's never used
    if (filter && !filter.is_common_narrow()) {
        search.open_search_bar_and_close_narrow_description();
    } else {
        const context = get_message_view_header_context(filter);
        append_and_display_title_area(context);
        search.close_search_bar_and_open_narrow_description();
    }
}

export function initialize(): void {
    render_title_area();

    const hide_stream_settings_button_width_threshold = 620;
    $("body").on("mouseenter mouseleave", ".narrow_description", function (event) {
        const $view_description_elt = $(this);
        const window_width = $(window).width()!;
        let hover_timeout;

        if (event.type === "mouseenter") {
            if (!$view_description_elt.hasClass("view-description-extended")) {
                const current_width = $view_description_elt.outerWidth();
                // Set fixed width for word-wrap to work
                $view_description_elt.css("width", current_width + "px");
            }
            hover_timeout = setTimeout(() => {
                $view_description_elt.addClass("view-description-extended");
                $(".top-navbar-container").addClass(
                    "top-navbar-container-allow-description-extension",
                );

                if (window_width <= hide_stream_settings_button_width_threshold) {
                    $(".message-header-stream-settings-button").hide();
                    // Let it expand naturally on smaller screens
                    $view_description_elt.css("width", "");
                }
            }, 250);
            $view_description_elt.data("hover_timeout", hover_timeout);
        } else if (event.type === "mouseleave") {
            // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
            hover_timeout = $view_description_elt.data("hover_timeout");
            if (typeof hover_timeout === "number") {
                // Clear any pending hover_timeout to prevent unexpected behavior
                clearTimeout(hover_timeout);
            }
            $view_description_elt.addClass("leaving-extended-view-description");

            // Wait for the reverse animation duration before cleaning up
            setTimeout(() => {
                $view_description_elt.removeClass("view-description-extended");
                $view_description_elt.removeClass("leaving-extended-view-description");
                if (window_width <= hide_stream_settings_button_width_threshold) {
                    $(".message-header-stream-settings-button").show();
                    $view_description_elt.css("width", "");
                } else {
                    // Reset to flexbox-determined width
                    $view_description_elt.css("width", "");
                }
            }, 100);
        }
    });
}

$("body").on("click", ".recap_button", (e) => {
    e.preventDefault();
    e.stopPropagation();

    const filter = narrow_state.filter();
    if (!filter) {
        return;
    }

    // We expect to be in a topic narrow
    if (!filter.has_operator("channel") || !filter.has_operator("topic")) {
        return;
    }

    const stream_operand = filter.terms_with_operator("channel")[0]!.operand;
    const topic_name_operand = filter.terms_with_operator("topic")[0]!.operand;

    const stream = stream_data.get_sub_by_id_string(stream_operand);
    const stream_name = stream ? stream.name : stream_operand;

    console.log("Recap request:", { stream_name, topic_name: topic_name_operand });

    const $button = $(e.currentTarget);
    const original_text = $button.text();
    $button.text($t({ defaultMessage: "Recapping..." }));
    $button.prop("disabled", true);

    void channel.get({
        url: "/json/messages/recap",
        data: {
            stream_name,
            topic_name: topic_name_operand,
        },
        success(data) {
            $button.text(original_text);
            $button.prop("disabled", false);
            const recap_text = (data as { recap: string }).recap;

            let html_body = recap_text;
            if (markdown.web_app_helpers) {
                const result = markdown.parse({
                    raw_content: recap_text,
                    helper_config: markdown.web_app_helpers
                });
                html_body = result.content;
            }

            const modal_id = dialog_widget.launch({
                html_heading: $t_html({ defaultMessage: "Topic Recap" }),
                html_body: `<div class="rendered_markdown" style="max-height: 70vh; overflow-y: auto;">${html_body}</div>`,
                html_submit_button: $t_html({ defaultMessage: "Close" }),
                hide_footer: true,
            });

            // Update dynamic elements (links, timestamps, etc.)
            const $modal = $(`#${modal_id}`);
            const $content = $modal.find(".rendered_markdown");
            rendered_markdown.update_elements($content);
        },
        error() {
            $button.text(original_text);
            $button.prop("disabled", false);
            // Handle error
            dialog_widget.launch({
                html_heading: $t_html({ defaultMessage: "Error" }),
                html_body: $t_html({ defaultMessage: "Failed to generate recap." }),
                hide_footer: true,
            });
        }
    });
});

$("body").on("click", ".suggest_title_button", (e) => {
    e.preventDefault();
    e.stopPropagation();

    const filter = narrow_state.filter();
    if (!filter) {
        return;
    }

    // We expect to be in a topic narrow
    if (!filter.has_operator("channel") || !filter.has_operator("topic")) {
        return;
    }

    const stream_operand = filter.terms_with_operator("channel")[0]!.operand;
    const topic_name_operand = filter.terms_with_operator("topic")[0]!.operand;

    const stream = stream_data.get_sub_by_id_string(stream_operand);
    if (!stream) {
        return;
    }

    console.log("Suggest Title request:", { stream_id: stream.stream_id, topic_name: topic_name_operand });

    const $button = $(e.currentTarget);
    const original_text = $button.text();
    $button.text($t({ defaultMessage: "Suggesting..." }));
    $button.prop("disabled", true);

    void channel.get({
        url: "/json/topic/suggest",
        data: {
            stream_id: Number(stream.stream_id),
            topic_name: topic_name_operand,
        },
        success(data) {
            $button.text(original_text);
            $button.prop("disabled", false);
            const suggestion = (data as { suggestion: string }).suggestion;

            dialog_widget.launch({
                html_heading: $t_html({ defaultMessage: "Suggested Topic Title" }),
                html_body: `<p>${$t({ defaultMessage: "AI suggests renaming this topic to:" })}</p><p><strong>${suggestion}</strong></p>`,
                html_submit_button: $t_html({ defaultMessage: "Apply" }),
                on_click() {
                    // Get the first message ID in the topic to use for renaming
                    // Fetch the first message using a separate API call
                    void channel.get({
                        url: "/json/messages",
                        data: {
                            narrow: JSON.stringify([
                                { operator: "channel", operand: stream.stream_id },
                                { operator: "topic", operand: topic_name_operand },
                            ]),
                            num_before: 0,
                            num_after: 1,
                            anchor: "oldest",
                        },
                        success(msg_data) {
                            const messages = (msg_data as { messages: Array<{ id: number }> }).messages;
                            if (messages.length > 0) {
                                const first_message_id = messages[0]!.id;
                                void channel.patch({
                                    url: `/json/messages/${first_message_id}`,
                                    data: {
                                        topic: suggestion,
                                        propagate_mode: "change_all",
                                    },
                                    success() {
                                        // Topic will be updated via event system
                                    },
                                    error() {
                                        dialog_widget.launch({
                                            html_heading: $t_html({ defaultMessage: "Error" }),
                                            html_body: $t_html({ defaultMessage: "Failed to rename topic." }),
                                            hide_footer: true,
                                        });
                                    }
                                });
                            }
                        },
                    });
                },
            });
        },
        error() {
            $button.text(original_text);
            $button.prop("disabled", false);
            dialog_widget.launch({
                html_heading: $t_html({ defaultMessage: "Error" }),
                html_body: $t_html({ defaultMessage: "Failed to get topic suggestion." }),
                hide_footer: true,
            });
        }
    });
});

export function render_title_area(): void {
    const filter = narrow_state.filter();
    build_message_view_header(filter);
}

// This function checks if "modified_sub" which is the stream whose values
// have been updated is the same as the stream which is currently
// narrowed and rerenders if necessary
export function maybe_rerender_title_area_for_stream(modified_stream_id: number): void {
    const current_stream_id = narrow_state.stream_id();

    if (current_stream_id === modified_stream_id) {
        render_title_area();
    }
}
