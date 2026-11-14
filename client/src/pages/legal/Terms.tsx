import { Link } from 'react-router-dom';
import LegalPage, { ContactDetails, Section, operatorName } from './LegalPage';

const Terms = () => (
    <LegalPage title="Terms of Use">
        {site => {
            const us = operatorName(site);
            const app = site?.app_name ?? 'the platform';
            return (
                <div className="space-y-10">
                    <p className="text-gray-300 leading-relaxed">
                        These terms apply when you use {app}, run by {us} ("we"). By creating an account or placing an order you agree to them.
                        Please also read our <Link to="/privacy" className="text-brand-500 hover:text-brand-400">Privacy Policy</Link>.
                    </p>

                    <Section title="1. What we do">
                        <p>
                            {app} is a marketplace. It lets you order from independent local restaurants and shops. <strong className="text-white">The restaurant
                            sells you the food, sets its prices and delivery fee, prepares your order and delivers it with its own drivers.</strong> We provide
                            the app that connects you; we are not the seller of the food.
                        </p>
                    </Section>

                    <Section title="2. Your account">
                        <ul className="list-disc pl-6 space-y-2">
                            <li>Give correct details, especially your cell number and delivery address, so your order reaches you.</li>
                            <li>Keep your password private. You are responsible for orders placed with your account.</li>
                            <li>We may suspend an account that is used for fraud, abuse of drivers or restaurant staff, or repeated fake orders.</li>
                        </ul>
                    </Section>

                    <Section title="3. Orders and prices">
                        <ul className="list-disc pl-6 space-y-2">
                            <li>Prices, the delivery fee and the total are shown before you place an order. The total you see is what you pay.</li>
                            <li>An order is confirmed when the restaurant accepts it. A restaurant may decline an order, for example if an item has run out.</li>
                            <li>Delivery times are estimates. Restaurants may limit how far they deliver.</li>
                            <li>Ask the restaurant about ingredients and allergens before ordering if this matters to you.</li>
                        </ul>
                    </Section>

                    <Section title="4. Paying">
                        <ul className="list-disc pl-6 space-y-2">
                            <li>You pay the restaurant, using a method it offers: cash or card machine on delivery, or online through PayFast, Ozow or Peach Payments.</li>
                            <li>For cash or card on delivery, have the amount ready when the driver arrives.</li>
                            <li>An online order is only sent to the restaurant once the payment company confirms the payment.</li>
                        </ul>
                    </Section>

                    <Section title="5. Cancelling and refunds">
                        <ul className="list-disc pl-6 space-y-2">
                            <li>To change or cancel an order, call the restaurant. Its number is shown on your order. Only the restaurant can cancel an order.</li>
                            <li>An online payment that is not completed is cancelled automatically, and you are not charged.</li>
                            <li>If a paid order is cancelled, the restaurant refunds you, because the restaurant received your money. You are told when a refund is due.</li>
                            <li>Your rights under the Consumer Protection Act, 2008 are not affected by these terms.</li>
                        </ul>
                    </Section>

                    <Section title="6. Restaurants on the platform">
                        <ul className="list-disc pl-6 space-y-2">
                            <li>Restaurants pay us a subscription for the plan they choose. The price, billing period and any order limit are shown before subscribing, and plans are paid in advance.</li>
                            <li>If a subscription is not paid, the restaurant stays visible for a short grace period and is then hidden from customers until it pays.</li>
                            <li>Restaurants are responsible for their food, prices, menus, food-safety compliance, their drivers and their staff, and for receiving payment from their customers.</li>
                            <li>A restaurant that enters its own PayFast, Ozow or Peach Payments details is responsible for that account.</li>
                        </ul>
                    </Section>

                    <Section title="7. Ratings">
                        <p>
                            Customers may rate orders that were delivered to them. Ratings must be honest and must not contain abuse or other people's personal
                            information. We may remove ratings that break this rule.
                        </p>
                    </Section>

                    <Section title="8. Our responsibility">
                        <p>
                            We work to keep {app} available and accurate, but cannot promise it will always be uninterrupted. To the extent the law allows,
                            we are not responsible for the quality, safety or delivery of food sold by restaurants, or for losses caused by a restaurant or
                            its driver. Nothing in these terms limits liability that cannot be limited by law.
                        </p>
                    </Section>

                    <Section title="9. Changes">
                        <p>We may update these terms. We will change the date at the top and tell you in the app about important changes.</p>
                    </Section>

                    <Section title="10. Law">
                        <p>These terms are governed by the law of the Republic of South Africa.</p>
                    </Section>

                    <Section title="11. Contact us">
                        <ContactDetails site={site} />
                    </Section>
                </div>
            );
        }}
    </LegalPage>
);

export default Terms;
